"""Komunálne (OSO) a krajské (OSK) voľby v Bratislave – ŠÚ SR (volby.statistics.sk, volbysr.sk).

Výstup: data/komunalne-bratislava.json

Pre každé voľby počíta:
  - primátor Bratislavy: kandidáti, hlasy, zvolený, účasť; víťaz v každej mestskej časti,
  - mestské zastupiteľstvo: zvolení poslanci po obvodoch (mestských častiach), mandáty podľa strán,
  - starostovia mestských častí: kandidáti, hlasy, zvolený, účasť,
  - miestne zastupiteľstvá: mandáty podľa strán,
  - predseda BSK: výsledok v Bratislave aj v celom kraji; poslanci BSK zvolení v Bratislave.

Zdroj sú balíky súborov ŠÚ SR (CSV, alebo XLSX ak CSV nie je). Pred zverejnením výsledkov
2026 sa uloží len stav „čaká sa na výsledky“. Mená kandidátov sú verejné údaje z kandidátnych
listín; vek, zamestnanie ani bydlisko nezverejňujeme.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

VYSTUP = Path(__file__).resolve().parent.parent / "data" / "komunalne-bratislava.json"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
MESTO = "582000"
VOLBY = [
    {"id": "2022", "datum": "2022-10-29", "nazov": "Komunálne a krajské voľby 2022",
     # archív volby.statistics.sk je od 23. 10. 2026 nedostupný – záloha z Internet Archive (kópia z 1. 12. 2024)
     "oso": ["https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip", "https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip"],
     "osk": ["https://volby.statistics.sk/osk/osk2022/files/OSK2022_SK_csv.zip"],
     "web": "https://volby.statistics.sk/oso/oso2022/sk/"},
    {"id": "2026", "datum": "2026-10-24", "nazov": "Komunálne a krajské voľby 2026",
     "oso": ["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip", "https://volbysr.sk/oso/files/OSO2026_SK_csv.zip"],
     "osk": ["https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip", "https://volbysr.sk/osk/files/OSK2026_SK_csv.zip"],
     "web": "https://volbysr.sk/oso/sk/"},
]

s = requests.Session()
s.headers["User-Agent"] = UA


# ---------- načítanie balíka ----------

# Hlavičky XLSX (slovné) → kódy stĺpcov ako v CSV
HLAVICKY = {
    "kód kraja": "KRAJ", "názov kraja": "NKRAJ", "kód územného obvodu": "OBVOD", "kód okresu": "OKRES",
    "kód obce": "OBEC", "kód mesta": "OBEC", "názov obce": "NOBEC", "názov mesta": "NOBEC",
    "volebný obvod v obci": "VOOBEC", "kód volebného obvodu": "VOBVOD", "názov volebného obvodu": "NVOBVOD", "okrsok": "OKRSOK",
    "poradie na hlasovacom lístku": "PC_HL", "meno": "MENO", "priezvisko": "PRIEZVISKO", "titul": "TITUL",
    "politický subjekt": "PS_TEXT", "počet platných hlasov": "P_HL", "podiel platných hlasov v %": "P_HL_PCT",
    "poznámka": "POZNAMKA", "kandidát": "KANDIDAT", "počet zapísaných voličov": "P_ZAP", "počet zúčastnených voličov": "P_ZUC",
    "počet odovzdaných obálok": "P_OO", "kód politickej strany": "PS", "názov politickej strany": "NPS", "skratka politickej strany": "SNPS",
}
IDENT = ("KRAJ", "VOBVOD", "OBEC", "VOOBEC", "OKRSOK", "PC_HL", "PS")


def normalizuj_kluc(nazov: str) -> str:
    """tab05f/tab05fx → tab05, tab0ad/tab0ax → tab0a, tab02bf/tab02bfx (2026: tab02f/tab02fx) → tab02b, tab0dd/tab0dx/tab0dc → tab0d."""
    n = nazov.lower()
    # 2026 (XLSX): účasť po okrskoch je tab02f/tab02fx (v 2022 tab02b); tab02b–e sú súhrny za obvody, okresy, obce
    if n.startswith("tab02f"):
        return "tab02b"
    if re.fullmatch(r"tab02[b-e]x?", n):
        return n + "_suhrn"
    for zaklad in ("tab0a", "tab0b", "tab0c", "tab0d", "tab02a", "tab02b", "tab05", "tab06", "tab08", "tab09"):
        if n.startswith(zaklad):
            return zaklad
    return n


def xlsx_riadky(obsah: bytes) -> list[dict]:
    from openpyxl import load_workbook  # len ak CSV nie je k dispozícii
    wb = load_workbook(io.BytesIO(obsah), read_only=True, data_only=True)
    riadky = list(wb.worksheets[0].iter_rows(values_only=True))
    for i, r in enumerate(riadky[:15]):
        hodnoty = [re.sub(r"\s+", " ", str(x).replace("_x000D_", " ")).strip().lower() if x is not None else "" for x in r]
        if sum(h in HLAVICKY for h in hodnoty) >= 2:
            hlavicka = [HLAVICKY.get(h, h) for h in hodnoty]
            return [{h: ("" if v is None else str(v)) for h, v in zip(hlavicka, rr) if h}
                    for rr in riadky[i + 1:] if any(v is not None for v in rr)]
    return []


def tabulky_z_balika(obsah: bytes) -> dict[str, list[dict]]:
    """ZIP s CSV alebo XLSX → {'tab05': [riadky], ...}. Varianty tej istej tabuľky (napr. obce + mestá BA/KE) sa zlúčia."""
    skupiny: dict[str, list[list[dict]]] = defaultdict(list)
    zf = zipfile.ZipFile(io.BytesIO(obsah))
    for meno_suboru in zf.namelist():
        m = re.search(r"_(tab[0-9a-z]+)\.(csv|xlsx)$", meno_suboru, re.I)
        if not m or "info" in meno_suboru.lower():
            continue
        surove = zf.read(meno_suboru)
        if meno_suboru.lower().endswith(".csv"):
            riadky = list(csv.DictReader(io.StringIO(surove.decode("utf-8-sig", errors="replace")), delimiter="|"))
        else:
            riadky = xlsx_riadky(surove)
        if riadky:
            skupiny[normalizuj_kluc(m.group(1))].append(riadky)
    vysledok: dict[str, list[dict]] = {}
    for kluc, subory in skupiny.items():
        # hlasy a účasť: len súbory po okrskoch; územie: len súbory s kódom obce; inak všetko
        if any("OKRSOK" in f[0] for f in subory):
            # súhrnné varianty (bez okrskov) slúžia len na príznak „zvolený“ (v XLSX nie je pri okrskoch)
            vysledok[kluc + "_agg"] = [r for f in subory if "OKRSOK" not in f[0] for r in f]
            subory = [f for f in subory if "OKRSOK" in f[0]]
        elif kluc == "tab0d" and any("OBEC" in f[0] for f in subory):
            subory = [f for f in subory if "OBEC" in f[0]]
        elif kluc in ("tab0a", "tab0b") and any("PC_HL" in f[0] and "MENO" in f[0] for f in subory):
            subory = [f for f in subory if "PC_HL" in f[0] and "MENO" in f[0]]
        # duplicity len medzi variantmi (napr. tab05f a tab05fx s tými istými riadkami); v rámci jedného súboru sa
        # kľúč môže legitímne opakovať – Košice číslujú okrsky v každej mestskej časti od 1 v rámci toho istého obvodu
        videne, riadky = set(), []
        for f in subory:
            kluce = [tuple(kod(r.get(c, "")) for c in IDENT) for r in f]
            riadky += [r for r, k in zip(f, kluce) if k not in videne]
            videne |= set(kluce)
        vysledok[kluc] = riadky
    return vysledok


def stiahni(urls: list[str]) -> tuple[dict[str, list[dict]] | None, str | None]:
    for u in urls:
        try:
            r = s.get(u, timeout=300)
        except requests.RequestException as e:
            print(f"  {u}: {e}")
            continue
        if r.status_code == 200 and r.content[:2] == b"PK":
            return tabulky_z_balika(r.content), u
        print(f"  {u}: HTTP {r.status_code}")
    return None, None


def cislo(x) -> float:
    try:
        return float(str(x).replace(",", ".").replace("\xa0", "").replace(" ", "") or 0)
    except ValueError:
        return 0.0


def kod(x) -> str:
    """Kódy z XLSX môžu prísť ako '582000.0'."""
    t = str(x).strip()
    return t[:-2] if t.endswith(".0") else t


# ---------- výpočty ----------

ZA_MENOM = {"PhD.", "CSc.", "DrSc.", "ArtD.", "MBA", "MA", "MPH", "LL.M.", "MSc.", "BSc.", "MPA", "DBA", "M.A.", "MHA"}


def meno(r: dict) -> str:
    tituly = [x.strip() for x in str(r.get("TITUL") or "").split(",") if x.strip()]
    pred = " ".join(t for t in tituly if t not in ZA_MENOM)
    za = ", ".join(t for t in tituly if t in ZA_MENOM)
    m = f"{r['MENO'].strip()} {r['PRIEZVISKO'].strip()}"
    return f"{pred + ' ' if pred else ''}{m}{', ' + za if za else ''}"


SKRATKY: dict[str, str] = {}  # skratka strany → plný názov (z tab0c), naplní strany_mapa


def je_zena(r: dict) -> bool:
    """Odhad podľa priezviska (slovenské ženské priezviská končia na -ová/-á); len pre súhrnné počty, nikdy pri mene."""
    p = str(r.get("PRIEZVISKO") or "").strip().split(" ")[-1].split("-")[-1].lower()
    return p.endswith("ová") or (p.endswith("á") and len(p) > 3)


def statistiky_poslancov(riadky: list[dict]) -> dict | None:
    """Súhrn za zvolených poslancov: počet žien (odhad z priezviska), vek (priemer, rozpätie, do 35 rokov)."""
    if not riadky:
        return None
    veky = [int(cislo(r.get("vek"))) for r in riadky if cislo(r.get("vek")) > 0]
    return {
        "zeny": sum(1 for r in riadky if je_zena(r)),
        **({"vek_priemer": round(sum(veky) / len(veky), 1), "vek_min": min(veky), "vek_max": max(veky), "do_35": sum(1 for v in veky if v <= 35)} if veky else {}),
    }


def strany_kandidata(r: dict, strany: dict[str, str]) -> str:
    text = str(r.get("PS_TEXT") or "").strip()
    kody = [k.strip() for k in str(r.get("PS") or "").split(",") if k.strip()]
    if not kody and text:
        if text.upper() == "NEKA":
            return "nezávislý kandidát"
        return ", ".join(SKRATKY.get(x.strip(), x.strip()) for x in text.split(", "))
    if not kody:
        return "nezávislý kandidát"
    return ", ".join(strany.get(kod(k)) or ("nezávislý kandidát" if kod(k).lstrip("0") in ("", "1") else kod(k)) for k in kody)


def zvoleny_flag(r: dict) -> str:
    """CSV: '1' zvolený, '0' náhradník, 'X' vzdal sa; XLSX: slovne."""
    v = str(r.get("KANDIDAT") or r.get("POZNAMKA") or "").strip().lower()
    if v in ("1", "1.0") or v.startswith("zvolen"):
        return "1"
    if v.startswith("náhrad") or v in ("0", "0.0"):
        return "0"
    if v == "x" or "vzdal" in v or "odvolan" in v:
        return "X"
    return ""


def vzdal_sa(r: dict) -> bool:
    v = str(r.get("POZNAMKA") or "").strip().lower()
    return v == "x" or "vzdal" in v or "odvolan" in v


def ucast(riadky: list[dict], obce: set[str], filtr=None) -> dict:
    zap = zuc = 0.0
    for r in riadky:
        if kod(r["OBEC"]) in obce and (filtr is None or filtr(r)):
            zap += cislo(r["P_ZAP"])
            zuc += cislo(r["P_ZUC"])
    return {"zapisani": int(zap), "volili": int(zuc), "ucast_pct": round(100 * zuc / zap, 2) if zap else None}


def vysledky_kandidatov(hlasy: list[dict], kandidati: list[dict], strany: dict[str, str], kluc_kand, filtr, zvol: set | None = None) -> list[dict]:
    """Súčet hlasov za okrsky → zoznam kandidátov zoradený podľa hlasov."""
    sucet: dict[tuple, float] = defaultdict(float)
    zvoleny: dict[tuple, str] = {}
    for r in hlasy:
        if not filtr(r):
            continue
        k = kluc_kand(r)
        sucet[k] += cislo(r["P_HL"])
        if zvoleny_flag(r):
            zvoleny[k] = zvoleny_flag(r)
    spolu = sum(sucet.values()) or 1
    out = []
    for r in kandidati:
        k = kluc_kand(r)
        if k not in sucet and not vzdal_sa(r):
            continue
        out.append({
            "meno": meno(r), "strany": strany_kandidata(r, strany),
            "hlasy": int(sucet.get(k, 0)), "podiel": round(100 * sucet.get(k, 0) / spolu, 2),
            "zvoleny": (k in zvol) if zvol is not None else zvoleny.get(k) == "1", "vzdal_sa": vzdal_sa(r),
            "_k": k,
        })
    out.sort(key=lambda x: -x["hlasy"])
    return out


def bez_klucov(zoznam: list[dict]) -> list[dict]:
    return [{k: v for k, v in x.items() if not k.startswith("_")} for x in zoznam]


def nazov_strany(n: str) -> str:
    """XLSX uvádza dvojjazyčné názvy („SZÖVETSÉG … | ALIANCIA …“), CSV len prvú časť – zjednotíme, aby sa ročníky dali porovnať."""
    return re.split(r"\s+\|\s+", (n or "").strip())[0].strip()


def strany_mapa(t: dict) -> dict[str, str]:
    for r in t.get("tab0c", []):
        if r.get("SNPS") and r.get("NPS"):
            SKRATKY[r["SNPS"].strip()] = nazov_strany(r["NPS"])
    return {kod(r.get("PS", "")): nazov_strany(r.get("NPS") or r.get("NSTR") or "") for r in t.get("tab0c", [])}


def zvoleni(t: dict, tab: str, kluc) -> set:
    """Kľúče zvolených kandidátov – z okrskových aj súhrnných riadkov."""
    return {kluc(r) for r in t.get(tab, []) + t.get(tab + "_agg", []) if zvoleny_flag(r) == "1" and r.get("PC_HL")}


def spracovanie(t: dict, obec: str) -> dict | None:
    """Priebežné výsledky: koľko okrskov obce už má výsledok (riadky tab02b) z celkového počtu (tab0d „počet okrskov“)."""
    riadok = next((r for r in t.get("tab0d", []) if kod(r.get("OBEC", "")) == obec), None)
    stlpec = next((k for k in (riadok or {}) if "okrs" in k.lower() and k != "OKRSOK"), None)
    spolu = int(cislo(riadok[stlpec])) if stlpec else 0
    hotove = sum(1 for r in t.get("tab02b", []) if kod(r.get("OBEC", "")) == obec)
    if not spolu:
        return None
    return {"okrsky": min(hotove, spolu), "spolu": spolu, "pct": round(100 * min(hotove, spolu) / spolu, 1), "priebezne": hotove < spolu}


def mandaty(zvoleni: list[dict]) -> list[dict]:
    pocty: dict[str, int] = defaultdict(int)
    for z in zvoleni:
        pocty[z["strany"]] += 1
    return [{"strany": k, "mandaty": v} for k, v in sorted(pocty.items(), key=lambda x: (-x[1], x[0]))]


def okrsky_mesta_na_mc(ucast_okrsky: list[dict], mc: list[str]) -> dict[tuple, str]:
    """Okrsok mesta (obvod, okrsok) → mestská časť. Ten istý fyzický okrsok má v tabuľke mesta aj mestskej časti
    rovnaký počet zapísaných a zúčastnených voličov; nejednoznačné prípady rozhodne väčšina v obvode."""
    podla_cisel: dict[tuple, set[str]] = defaultdict(set)
    for r in ucast_okrsky:
        if kod(r["OBEC"]) in mc:
            podla_cisel[(int(cislo(r["P_ZAP"])), int(cislo(r["P_ZUC"])))].add(kod(r["OBEC"]))
    mapa: dict[tuple, str] = {}
    nejasne: dict[tuple, set[str]] = {}
    for r in ucast_okrsky:
        if kod(r["OBEC"]) != MESTO:
            continue
        k = (kod(r.get("VOOBEC", "")), kod(r["OKRSOK"]))
        kandidati = podla_cisel.get((int(cislo(r["P_ZAP"])), int(cislo(r["P_ZUC"]))), set())
        if len(kandidati) == 1:
            mapa[k] = next(iter(kandidati))
        elif kandidati:
            nejasne[k] = kandidati
    for k, kandidati in nejasne.items():
        v_obvode = [mc_ for (o, _), mc_ in mapa.items() if o == k[0] and mc_ in kandidati]
        mapa[k] = max(kandidati, key=v_obvode.count) if v_obvode else sorted(kandidati)[0]
    return mapa


def primator_po_mc(t: dict[str, list[dict]], mesto: str, predpona: str, strany: dict[str, str]) -> tuple[list[dict], dict]:
    """Voľba primátora podľa mestských častí (Bratislava, Košice). Tabuľky mesta majú okrsky len ako (obvod, okrsok);
    v Košiciach sa číslo okrsku v obvode opakuje (každá MČ čísluje od 1), preto okrsky rozlišujeme aj poradím výskytu.
    Okrsok mesta → MČ podľa zhody počtu zapísaných a zúčastnených voličov s tabuľkou MČ.
    Vráti (zoznam MČ, kontrola), kontrola = počty priradených okrskov a okrskov, kde hlasy prevyšujú voličov."""
    uzemie = t.get("tab0d", [])
    mc = {kod(r["OBEC"]): r["NOBEC"].split(" - ", 1)[1].strip() for r in uzemie
          if kod(r["OBEC"]) != mesto and (r.get("NOBEC") or "").startswith(predpona + " - ")}
    ucast_rows = t.get("tab02b", [])
    podla_cisel: dict[tuple, set[str]] = defaultdict(set)
    for r in ucast_rows:
        if kod(r["OBEC"]) in mc:
            podla_cisel[(int(cislo(r["P_ZAP"])), int(cislo(r["P_ZUC"])))].add(kod(r["OBEC"]))
    # okrsky mesta s poradím výskytu kľúča
    vyskyt: dict[tuple, int] = defaultdict(int)
    okrsky: dict[tuple, dict] = {}
    for r in ucast_rows:
        if kod(r["OBEC"]) != mesto:
            continue
        k = (kod(r.get("VOOBEC", "")), kod(r["OKRSOK"]))
        okrsky[(*k, vyskyt[k])] = r
        vyskyt[k] += 1
    na_mc: dict[tuple, str] = {}
    nejasne: dict[tuple, set[str]] = {}
    podla_zap: dict[int, set[str]] = defaultdict(set)
    for r in ucast_rows:
        if kod(r["OBEC"]) in mc:
            podla_zap[int(cislo(r["P_ZAP"]))].add(kod(r["OBEC"]))
    for k3, r in okrsky.items():
        # najprv zapísaní + zúčastnení, inak len zapísaní (zúčastnení sa v tabuľke mesta a MČ niekedy líšia o pár voličov)
        kand = podla_cisel.get((int(cislo(r["P_ZAP"])), int(cislo(r["P_ZUC"]))), set()) or podla_zap.get(int(cislo(r["P_ZAP"])), set())
        if len(kand) == 1:
            na_mc[k3] = next(iter(kand))
        elif kand:
            nejasne[k3] = kand
    for k3, kand in nejasne.items():
        v_obvode = [m for kk, m in na_mc.items() if kk[0] == k3[0] and m in kand]
        na_mc[k3] = max(sorted(kand), key=v_obvode.count) if v_obvode else sorted(kand)[0]
    # hlasy primátora po okrskoch. Pri opakovanom čísle okrsku (Košice: každá MČ čísluje od 1) sú riadky v tab05 rovnakého
    # kľúča premiešané a poradie nezodpovedá okrskom. Okrsok riadku preto určíme z podielu: P_HL / (P_HL_PCT / 100) =
    # počet platných hlasov pre starostu v okrsku (P_HL_STA v tab02b) – ten sa medzi okrskami s rovnakým číslom líši.
    def sta(r: dict) -> float:
        return cislo(r.get("P_HL_STA") or r.get("počet platných hlasovacích lístkov odovzdaných pre voľby starostu") or 0)
    po_okrsku: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    v_okrsku: dict[tuple, float] = defaultdict(float)
    hlasy: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    ciele_k: dict[tuple, list[tuple]] = defaultdict(list)
    for k3 in okrsky:
        ciele_k[k3[:2]].append(k3)
    poradie_kand: dict[tuple, int] = defaultdict(int)
    for r in t.get("tab05", []):
        if kod(r["OBEC"]) != mesto:
            continue
        k = (kod(r.get("VOOBEC", "")), kod(r["OKRSOK"]))
        pc_, n = kod(r["PC_HL"]), cislo(r["P_HL"])
        ciele = ciele_k.get(k) or [(*k, 0)]
        if len(ciele) == 1:
            k3 = ciele[0]
        else:
            pct = cislo(r.get("P_HL_PCT", ""))
            if n > 0 and pct > 0 and all(sta(okrsky[c]) for c in ciele):
                odhad = n * 100 / pct
                k3 = min(ciele, key=lambda c: abs(sta(okrsky[c]) - odhad))
            else:  # 0 hlasov alebo chýba podiel – na súčtoch nezáleží, poradie výskytu
                i = poradie_kand[(*k, pc_)] % len(ciele)
                k3 = sorted(ciele)[i]
        poradie_kand[(*k, pc_)] += 1
        po_okrsku[k3][pc_] += n
    for k3, v in po_okrsku.items():
        v_okrsku[k3] = sum(v.values())
        m = na_mc.get(k3)
        if m:
            for pc_, n in v.items():
                hlasy[m][pc_] += n
    kand_prim = {kod(r["PC_HL"]): r for r in t.get("tab0a", []) if kod(r["OBEC"]) == mesto}
    vysl = []
    for m, nazov in mc.items():
        h = hlasy.get(m)
        if not h or not sum(h.values()):
            continue
        spolu = sum(h.values())
        u = ucast([r for k3, r in okrsky.items() if na_mc.get(k3) == m], {mesto})
        por = sorted(h.items(), key=lambda kv: -kv[1])
        vysl.append({"kod": m, "nazov": nazov, "ucast": u["ucast_pct"], "volili": u["volili"],
                     "poradie": [{"meno": meno(kand_prim[pc]), "strany": strany_kandidata(kand_prim[pc], strany), "hlasy": int(v), "podiel": round(100 * v / spolu, 2)}
                                 for pc, v in por[:3] if pc in kand_prim]})
    vysl.sort(key=lambda x: x["nazov"])
    nad = sum(1 for k3, v in v_okrsku.items() if k3 in okrsky and v > cislo(okrsky[k3]["P_ZUC"]))
    return vysl, {"okrskov": len(okrsky), "priradenych": len(na_mc), "hlasy_nad_volicov": nad}


def spracuj_oso(t: dict[str, list[dict]], nazvy_mc: dict[str, str]) -> dict:
    strany = strany_mapa(t)
    uzemie = t["tab0d"]
    mc = sorted({kod(r["OBEC"]) for r in uzemie if kod(r["OBEC"]) != MESTO and "Bratislava -" in (r.get("NOBEC") or "")})
    for r in uzemie:
        if kod(r["OBEC"]) in mc:
            nazvy_mc.setdefault(kod(r["OBEC"]), r["NOBEC"].replace("Bratislava - ", "").strip())
    ucast_okrsky = t["tab02b"]
    okrsok_mc = okrsky_mesta_na_mc(ucast_okrsky, mc)
    mesto_okrsky = sum(1 for r in ucast_okrsky if kod(r["OBEC"]) == MESTO)

    # Primátor – spolu a podľa mestských častí (cez okrsky)
    kand_prim = [r for r in t["tab0a"] if kod(r["OBEC"]) == MESTO]
    hl_prim = [r for r in t["tab05"] if kod(r["OBEC"]) == MESTO]
    pc = lambda r: kod(r["PC_HL"])  # noqa: E731
    zvol_sta = zvoleni(t, "tab05", lambda r: (kod(r["OBEC"]), kod(r["PC_HL"])))
    zvol_pos = zvoleni(t, "tab08", lambda r: (kod(r["OBEC"]), kod(r.get("VOOBEC", "")), kod(r["PC_HL"])))
    primator = vysledky_kandidatov(hl_prim, kand_prim, strany, pc, lambda r: True, {k[1] for k in zvol_sta if k[0] == MESTO})
    okr = lambda r: (kod(r.get("VOOBEC", "")), kod(r["OKRSOK"]))  # noqa: E731
    prim_mc = []
    for kod_mc in mc:
        v = vysledky_kandidatov(hl_prim, kand_prim, strany, pc, lambda r, m=kod_mc: okrsok_mc.get(okr(r)) == m)
        if not v or not sum(x["hlasy"] for x in v):
            continue
        u = ucast([r for r in ucast_okrsky if kod(r["OBEC"]) == MESTO and okrsok_mc.get(okr(r)) == kod_mc], {MESTO})
        prim_mc.append({"kod": kod_mc, "nazov": nazvy_mc.get(kod_mc, kod_mc), "ucast": u["ucast_pct"],
                        "poradie": [{"meno": x["meno"], "podiel": x["podiel"]} for x in v[:3]]})
    prim_mc.sort(key=lambda x: x["nazov"])

    # Obvody mesta → názvy mestských častí, ktoré tvoria obvod
    obvod_casti: dict[str, set[str]] = defaultdict(set)
    for (obvod, _), kod_mc in okrsok_mc.items():
        obvod_casti[obvod].add(nazvy_mc.get(kod_mc, kod_mc))
    nazov_obvodu = lambda o: ", ".join(sorted(obvod_casti.get(o, []))) or f"obvod {o}"  # noqa: E731

    # Mestské zastupiteľstvo – len zvolení
    kand_msz = {(kod(r["VOOBEC"]), kod(r["PC_HL"])): r for r in t["tab0b"] if kod(r["OBEC"]) == MESTO}
    hl_msz: dict[tuple, float] = defaultdict(float)
    zvoleni_msz: set[tuple] = set()
    for r in t["tab08"]:
        if kod(r["OBEC"]) != MESTO:
            continue
        k = (kod(r["VOOBEC"]), kod(r["PC_HL"]))
        hl_msz[k] += cislo(r["P_HL"])
        if (MESTO, k[0], k[1]) in zvol_pos:
            zvoleni_msz.add(k)
    msz = [{"obvod": nazov_obvodu(k[0]), "meno": meno(kand_msz[k]), "strany": strany_kandidata(kand_msz[k], strany), "hlasy": int(hl_msz[k])}
           for k in sorted(zvoleni_msz, key=lambda k: (nazov_obvodu(k[0]), -hl_msz[k], k)) if k in kand_msz]
    stat_msz = statistiky_poslancov([kand_msz[x] for x in zvoleni_msz if x in kand_msz])

    # Starostovia a miestne zastupiteľstvá
    starostovia = []
    for kod_mc in mc:
        kand = [r for r in t["tab0a"] if kod(r["OBEC"]) == kod_mc]
        hl = [r for r in t["tab05"] if kod(r["OBEC"]) == kod_mc]
        v = vysledky_kandidatov(hl, kand, strany, pc, lambda r: True, {k[1] for k in zvol_sta if k[0] == kod_mc})
        kand_mz = {(kod(r["VOOBEC"]), kod(r["PC_HL"])): r for r in t["tab0b"] if kod(r["OBEC"]) == kod_mc}
        zvol_kluce = {(k[1], k[2]) for k in zvol_pos if k[0] == kod_mc}
        zvol = [{"strany": strany_kandidata(kand_mz[k], strany)} for k in zvol_kluce if k in kand_mz]
        starostovia.append({
            "kod": kod_mc, "nazov": nazvy_mc.get(kod_mc, kod_mc), "ucast": ucast(ucast_okrsky, {kod_mc}),
            "kandidati": bez_klucov(v), "miestne_zastupitelstvo": {"poslancov": len(zvol), "mandaty": mandaty(zvol)},
        })
    starostovia.sort(key=lambda x: x["nazov"])
    # ak párovanie okrskov podľa voličov nepokrylo všetky MČ (2026: 15/17), použiť metódu z primator_po_mc
    # (párovanie cez platné hlasy pre voľbu starostu) – rovnaká štruktúra (kod, nazov, ucast, poradie)
    if len(prim_mc) < len(mc):
        alt, kontrola = primator_po_mc(t, MESTO, "Bratislava", strany)
        if len(alt) > len(prim_mc) and not kontrola.get("hlasy_nad_volicov"):
            prim_mc = [{"kod": x["kod"], "nazov": nazvy_mc.get(x["kod"], x["nazov"]), "ucast": x["ucast"],
                        "poradie": [{"meno": p["meno"], "podiel": p["podiel"]} for p in x["poradie"]]} for x in alt]
            print(f"  MČ podľa platných hlasov: {len(prim_mc)}, okrsky {kontrola}")

    return {
        "primator": {"ucast": ucast(ucast_okrsky, {MESTO}), "kandidati": bez_klucov(primator), "mestske_casti": prim_mc,
                     "okrsky_priradene": f"{len(okrsok_mc)}/{mesto_okrsky}"},
        "mestske_zastupitelstvo": {"poslancov": len(msz), "obvodov": len(obvod_casti), "mandaty": mandaty(msz), "zvoleni": msz, **({"statistiky": stat_msz} if stat_msz else {})},
        "starostovia": starostovia,
    }


def _tab_ucast(t: dict[str, list[dict]]) -> list[dict]:
    """Účasť po okrskoch alebo obciach: 2022 tab02b; 2026 OSO tab02f(x) → tab02b, OSK tab02d (okrsky) / tab02c (obce)."""
    for k in ("tab02b", "tab02d_suhrn", "tab02c_suhrn"):
        r = [x for x in t.get(k, []) if x.get("OBEC") and x.get("P_ZAP")]
        if r:
            return r
    return []


def spracuj_osk(t: dict[str, list[dict]], nazvy_mc: dict[str, str]) -> dict:
    strany = strany_mapa(t)
    uzemie = t["tab0d"]
    kraj_obce = {kod(r["OBEC"]) for r in uzemie if kod(r["KRAJ"]) == "1"}
    ba_obce = {kod(r["OBEC"]) for r in uzemie if kod(r["KRAJ"]) == "1" and "Bratislava -" in (r.get("NOBEC") or "")}
    ba_obvody = {kod(r["VOBVOD"]) for r in uzemie if kod(r["OBEC"]) in ba_obce}
    kand = [r for r in t["tab0a"] if kod(r["KRAJ"]) == "1"]
    pc = lambda r: kod(r["PC_HL"])  # noqa: E731
    vsetky06 = t.get("tab06", []) + t.get("tab06_agg", [])
    zvol_pred = {kod(r["PC_HL"]) for r in vsetky06
                 if zvoleny_flag(r) == "1" and r.get("PC_HL") and (not r.get("KRAJ") or kod(r["KRAJ"]) == "1") and (not r.get("OBEC") or kod(r["OBEC"]) in kraj_obce)}
    # hlasy za predsedu: riadky s obcou (2026 je v tab06 aj súhrn za kraj bez obce – ten nesčítavame)
    hl06 = [r for r in t.get("tab06", []) if r.get("OBEC")]
    predseda_kraj = vysledky_kandidatov(hl06, kand, strany, pc, lambda r: kod(r["OBEC"]) in kraj_obce, zvol_pred)
    predseda_ba = vysledky_kandidatov(hl06, kand, strany, pc, lambda r: kod(r["OBEC"]) in ba_obce)
    obec_obvod = {kod(r["OBEC"]): kod(r["VOBVOD"]) for r in uzemie}
    kand_pos = {(kod(r["VOBVOD"]), kod(r["PC_HL"])): r for r in t["tab0b"] if kod(r["VOBVOD"]) in ba_obvody}
    # hlasy poslancov: súhrn za volebný obvod, ak je; inak súčet za obce alebo okrsky (nikdy viac úrovní naraz)
    riadky09 = t.get("tab09", []) + t.get("tab09_agg", [])
    uroven = lambda r: "okrsok" if r.get("OKRSOK") else "obec" if r.get("OBEC") else "obvod"  # noqa: E731
    urovne = {uroven(r) for r in riadky09 if r.get("P_HL")}
    pouzi = next((u for u in ("obvod", "obec", "okrsok") if u in urovne), None)
    hl: dict[tuple, float] = defaultdict(float)
    zvol: set[tuple] = set()
    for r in riadky09:
        vo = kod(r["VOBVOD"]) if r.get("VOBVOD") else obec_obvod.get(kod(r.get("OBEC", "")))
        if vo not in ba_obvody or not r.get("PC_HL"):
            continue
        k = (vo, kod(r["PC_HL"]))
        if uroven(r) == pouzi and r.get("P_HL"):
            hl[k] += cislo(r["P_HL"])
        if zvoleny_flag(r) == "1":
            zvol.add(k)
    nazov_obvodu: dict[str, set[str]] = defaultdict(set)
    for r in uzemie:
        if kod(r["VOBVOD"]) in ba_obvody:
            nazov_obvodu[kod(r["VOBVOD"])].add(nazvy_mc.get(kod(r["OBEC"]), r["NOBEC"].replace("Bratislava - ", "")))
    poslanci = [{"obvod": ", ".join(sorted(nazov_obvodu.get(k[0], {k[0]}))), "meno": meno(kand_pos[k]), "strany": strany_kandidata(kand_pos[k], strany), "hlasy": int(hl[k])}
                for k in sorted(zvol, key=lambda k: (k[0], -hl[k], k)) if k in kand_pos]
    u = _tab_ucast(t)
    return {
        "predseda": {
            "kraj": {"ucast": ucast(u, kraj_obce), "kandidati": bez_klucov(predseda_kraj)},
            "bratislava": {"ucast": ucast(u, ba_obce), "kandidati": [{"meno": x["meno"], "hlasy": x["hlasy"], "podiel": x["podiel"]} for x in predseda_ba]},
        },
        "poslanci_za_bratislavu": {"poslancov": len(poslanci), "mandaty": mandaty(poslanci), "zvoleni": poslanci},
    }


def main() -> int:
    stary = json.loads(VYSTUP.read_text(encoding="utf-8")) if VYSTUP.exists() else {}
    stare_volby = {v["id"]: v for v in stary.get("volby", [])}
    vystup = {"zdroj": {"nazov": "Štatistický úrad SR – výsledky volieb do orgánov samosprávy obcí a samosprávnych krajov", "url": "https://volbysr.sk"}, "volby": []}
    chyby = []
    for v in VOLBY:
        print(f"{v['nazov']}:")
        zaznam = {k: v[k] for k in ("id", "datum", "nazov", "web")}
        nazvy_mc: dict[str, str] = {}
        try:
            oso, url_oso = stiahni(v["oso"])
            osk, url_osk = stiahni(v["osk"])
            ma_oso = bool(oso and oso.get("tab05") and oso.get("tab0a"))
            ma_osk = bool(osk and osk.get("tab06") and osk.get("tab0a"))
            if ma_oso:
                zaznam["oso"] = spracuj_oso(oso, nazvy_mc)
                zaznam["zdroj_oso"] = url_oso
            if ma_osk:
                zaznam["osk"] = spracuj_osk(osk, nazvy_mc)
                zaznam["zdroj_osk"] = url_osk
            zaznam["stav"] = "vysledky" if ma_oso else ("kandidati" if oso and oso.get("tab0a") else "caka_sa")
            if ma_oso:
                zaznam["spracovanie"] = spracovanie(oso, MESTO)
            if zaznam["stav"] == "kandidati":
                # pred voľbami: len zoznamy kandidátov na primátora a predsedu BSK
                strany_o = strany_mapa(oso)
                zaznam["kandidati_primator"] = [{"meno": meno(r), "strany": strany_kandidata(r, strany_o)}
                                                for r in sorted(oso["tab0a"], key=lambda r: int(cislo(r["PC_HL"]))) if kod(r["OBEC"]) == MESTO and not vzdal_sa(r)]
                if osk and osk.get("tab0a"):
                    strany_k = strany_mapa(osk)
                    zaznam["kandidati_predseda_bsk"] = [{"meno": meno(r), "strany": strany_kandidata(r, strany_k)}
                                                        for r in sorted(osk["tab0a"], key=lambda r: int(cislo(r["PC_HL"]))) if kod(r.get("KRAJ", "")) == "1" and not vzdal_sa(r)]
            if ma_oso and not ma_osk and stare_volby.get(v["id"], {}).get("osk"):
                zaznam["osk"] = stare_volby[v["id"]]["osk"]  # krajské voľby: zdroj nedostupný, ponechať uložené
                zaznam["zdroj_osk"] = stare_volby[v["id"]].get("zdroj_osk")
            stare_konecne = v["id"] in stare_volby and stare_volby[v["id"]].get("stav") == "vysledky" \
                and not (stare_volby[v["id"]].get("spracovanie") or {}).get("zdroj")  # priebežné z JSON nie sú konečné
            if not ma_oso and stare_konecne:
                zaznam = stare_volby[v["id"]]  # výsledky už máme, server dočasne nedostupný
            elif not ma_oso and v["id"] == "2026":
                # počas sčítavania: priebežný primátor z JSON stránky ŠÚ SR (balík XLSX príde až s konečnými výsledkami)
                import volby_priebezne as vp
                d = vp.mesto("bratislava")
                if d:
                    zaznam["stav"] = "vysledky"
                    zaznam["spracovanie"] = d["spracovanie"]
                    zaznam["oso"] = {"primator": {"ucast": d["ucast"], "kandidati": d["primator"], "mestske_casti": [], "okrsky_priradene": 0},
                                     "mestske_zastupitelstvo": {"poslancov": 0, "mandaty": [], "zvoleni": []}, "starostovia": vp.starostovia_ba()}
                    zaznam["zdroj_oso"] = "https://volbysr.sk/oso/sk/vysledky_obce.html"
            if zaznam.get("oso"):
                p = zaznam["oso"]["primator"]
                vit = next((k for k in p["kandidati"] if k["zvoleny"]), p["kandidati"][0] if p["kandidati"] else None)
                print(f"  primátor: {vit and vit['meno']} {vit and vit['podiel']} %, účasť {p['ucast']['ucast_pct']} %, MČ v rozdelení {len(p['mestske_casti'])}/17, okrsky {p['okrsky_priradene']}, "
                      f"MsZ {zaznam['oso']['mestske_zastupitelstvo']['poslancov']}, starostovia {len(zaznam['oso']['starostovia'])}")
            if zaznam.get("osk"):
                pk = zaznam["osk"]["predseda"]["kraj"]
                print(f"  predseda BSK: {pk['kandidati'][0]['meno']} {pk['kandidati'][0]['podiel']} %, poslanci za BA {zaznam['osk']['poslanci_za_bratislavu']['poslancov']}")
            print(f"  stav: {zaznam.get('stav')}")
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{v['id']}: {type(e).__name__}: {e}")
            if v["id"] in stare_volby:
                zaznam = stare_volby[v["id"]]
            else:
                zaznam["stav"] = "caka_sa"
        vystup["volby"].append(zaznam)

    if stary.get("volby") != vystup["volby"]:
        vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        VYSTUP.write_text(json.dumps(vystup, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("Uložené.")
    else:
        print("Bez zmeny.")
    if chyby:
        raise RuntimeError("; ".join(chyby))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber komunálnych volieb::{type(e).__name__}: {sprava}")
        sys.exit(1)
