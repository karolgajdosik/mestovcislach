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
     "oso": ["https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip"],
     "osk": ["https://volby.statistics.sk/osk/osk2022/files/OSK2022_SK_csv.zip"],
     "web": "https://volby.statistics.sk/oso/oso2022/sk/"},
    {"id": "2026", "datum": "2026-10-24", "nazov": "Komunálne a krajské voľby 2026",
     "oso": ["https://volbysr.sk/oso/files/OSO2026_SK_csv.zip", "https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"],
     "osk": ["https://volbysr.sk/osk/files/OSK2026_SK_csv.zip", "https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip"],
     "web": "https://volbysr.sk/oso/sk/"},
]

s = requests.Session()
s.headers["User-Agent"] = UA


# ---------- načítanie balíka ----------

def tabulky_z_balika(obsah: bytes) -> dict[str, list[dict]]:
    """ZIP s CSV alebo XLSX → {'tab05': [riadky], ...} (kľúč = 'tab' + číslo/písmeno bez koncového písmena verzie)."""
    vysledok: dict[str, list[dict]] = {}
    zf = zipfile.ZipFile(io.BytesIO(obsah))
    for meno in zf.namelist():
        m = re.search(r"_(tab[0-9a-z]+?)([a-z]?)\.(csv|xlsx)$", meno, re.I)
        if not m or "info" in meno.lower():
            continue
        kluc = normalizuj_kluc(m.group(1) + m.group(2))
        surove = zf.read(meno)
        if meno.lower().endswith(".csv"):
            text = surove.decode("utf-8-sig", errors="replace")
            riadky = list(csv.DictReader(io.StringIO(text), delimiter="|"))
        else:
            riadky = xlsx_riadky(surove)
        # viac verzií tej istej tabuľky (napr. tab0db a tab0dc) – ponechať tú s kódom obce
        if kluc in vysledok and vysledok[kluc] and "OBEC" in vysledok[kluc][0] and not (riadky and "OBEC" in riadky[0]):
            continue
        vysledok[kluc] = riadky
    return vysledok


def normalizuj_kluc(nazov: str) -> str:
    """tab05f → tab05, tab0ad → tab0a, tab02bf → tab02b, tab0dd → tab0d (posledné písmeno je verzia súboru)."""
    n = nazov.lower()
    for zaklad in ("tab0a", "tab0b", "tab0c", "tab0d", "tab02a", "tab02b", "tab05", "tab06", "tab08", "tab09"):
        if n.startswith(zaklad):
            return zaklad
    return n


def xlsx_riadky(obsah: bytes) -> list[dict]:
    from openpyxl import load_workbook  # len ak CSV nie je k dispozícii
    wb = load_workbook(io.BytesIO(obsah), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    riadky = list(ws.iter_rows(values_only=True))
    # hlavička = prvý riadok, ktorý obsahuje „OBEC“ / „KRAJ“ / „PS“ / „VOBVOD“
    for i, r in enumerate(riadky[:15]):
        hodnoty = [str(x).strip() if x is not None else "" for x in r]
        if any(h in hodnoty for h in ("OBEC", "KRAJ", "PS", "VOBVOD")):
            hlavicka = hodnoty
            return [{h: ("" if v is None else str(v)) for h, v in zip(hlavicka, rr) if h} for rr in riadky[i + 1:] if any(v is not None for v in rr)]
    return []


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


def strany_kandidata(r: dict, strany: dict[str, str]) -> str:
    kody = [k.strip() for k in str(r.get("PS") or "").split(",") if k.strip()]
    if not kody:
        return "nezávislý kandidát"
    return ", ".join(strany.get(kod(k), k) for k in kody)


def ucast(riadky: list[dict], obce: set[str], filtr=None) -> dict:
    zap = zuc = 0.0
    for r in riadky:
        if kod(r["OBEC"]) in obce and (filtr is None or filtr(r)):
            zap += cislo(r["P_ZAP"])
            zuc += cislo(r["P_ZUC"])
    return {"zapisani": int(zap), "volili": int(zuc), "ucast_pct": round(100 * zuc / zap, 2) if zap else None}


def vysledky_kandidatov(hlasy: list[dict], kandidati: list[dict], strany: dict[str, str], kluc_kand, filtr) -> list[dict]:
    """Súčet hlasov za okrsky → zoznam kandidátov zoradený podľa hlasov."""
    sucet: dict[tuple, float] = defaultdict(float)
    zvoleny: dict[tuple, str] = {}
    for r in hlasy:
        if not filtr(r):
            continue
        k = kluc_kand(r)
        sucet[k] += cislo(r["P_HL"])
        if str(r.get("KANDIDAT") or "").strip():
            zvoleny[k] = str(r["KANDIDAT"]).strip()
    spolu = sum(sucet.values()) or 1
    out = []
    for r in kandidati:
        k = kluc_kand(r)
        if k not in sucet and str(r.get("POZNAMKA") or "").strip().upper() != "X":
            continue
        out.append({
            "meno": meno(r), "strany": strany_kandidata(r, strany),
            "hlasy": int(sucet.get(k, 0)), "podiel": round(100 * sucet.get(k, 0) / spolu, 2),
            "zvoleny": zvoleny.get(k) == "1", "vzdal_sa": str(r.get("POZNAMKA") or "").strip().upper() == "X",
            "_k": k,
        })
    out.sort(key=lambda x: -x["hlasy"])
    return out


def bez_klucov(zoznam: list[dict]) -> list[dict]:
    return [{k: v for k, v in x.items() if not k.startswith("_")} for x in zoznam]


def mandaty(zvoleni: list[dict]) -> list[dict]:
    pocty: dict[str, int] = defaultdict(int)
    for z in zvoleni:
        pocty[z["strany"]] += 1
    return [{"strany": k, "mandaty": v} for k, v in sorted(pocty.items(), key=lambda x: -x[1])]


def spracuj_oso(t: dict[str, list[dict]], nazvy_mc: dict[str, str]) -> dict:
    strany = {kod(r["PS"] if "PS" in r else r.get("STR")): (r.get("NPS") or r.get("NSTR") or "").strip() for r in t["tab0c"]}
    uzemie = t["tab0d"]
    mc = sorted({kod(r["OBEC"]) for r in uzemie if kod(r["OBEC"]) != MESTO and "Bratislava -" in (r.get("NOBEC") or "")})
    for r in uzemie:
        if kod(r["OBEC"]) in mc:
            nazvy_mc.setdefault(kod(r["OBEC"]), r["NOBEC"].replace("Bratislava - ", "").strip())
    ucast_okrsky = t["tab02b"]

    # Primátor
    kand_prim = [r for r in t["tab0a"] if kod(r["OBEC"]) == MESTO]
    hl_prim = [r for r in t["tab05"] if kod(r["OBEC"]) == MESTO]
    primator = vysledky_kandidatov(hl_prim, kand_prim, strany, lambda r: kod(r["PC_HL"]), lambda r: True)

    # Obvody mesta (VOOBEC) → mestské časti: zhoda počtu zapísaných voličov
    zap_obvod: dict[str, float] = defaultdict(float)
    for r in ucast_okrsky:
        if kod(r["OBEC"]) == MESTO:
            zap_obvod[kod(r["VOOBEC"])] += cislo(r["P_ZAP"])
    zap_mc: dict[str, float] = defaultdict(float)
    for r in ucast_okrsky:
        if kod(r["OBEC"]) in mc:
            zap_mc[kod(r["OBEC"])] += cislo(r["P_ZAP"])
    obvod_mc: dict[str, str] = {}
    volne = dict(zap_mc)
    for obvod, zap in sorted(zap_obvod.items(), key=lambda x: -x[1]):
        if not volne:
            break
        najblizsia = min(volne, key=lambda k: abs(volne[k] - zap))
        if abs(volne[najblizsia] - zap) <= max(50, 0.02 * zap):
            obvod_mc[obvod] = najblizsia
            del volne[najblizsia]

    prim_mc = []
    for obvod, kod_mc in sorted(obvod_mc.items(), key=lambda x: nazvy_mc.get(x[1], "")):
        v = vysledky_kandidatov(hl_prim, kand_prim, strany, lambda r: kod(r["PC_HL"]), lambda r, o=obvod: kod(r["VOOBEC"]) == o)
        prim_mc.append({"kod": kod_mc, "nazov": nazvy_mc.get(kod_mc, kod_mc), "ucast": ucast([r for r in ucast_okrsky if kod(r["OBEC"]) == MESTO and kod(r["VOOBEC"]) == obvod], {MESTO})["ucast_pct"],
                        "poradie": [{"meno": x["meno"], "podiel": x["podiel"]} for x in v[:3]]})

    # Mestské zastupiteľstvo – len zvolení
    kand_msz = {(kod(r["VOOBEC"]), kod(r["PC_HL"])): r for r in t["tab0b"] if kod(r["OBEC"]) == MESTO}
    hl_msz: dict[tuple, float] = defaultdict(float)
    zvoleni_msz: set[tuple] = set()
    for r in t["tab08"]:
        if kod(r["OBEC"]) != MESTO:
            continue
        k = (kod(r["VOOBEC"]), kod(r["PC_HL"]))
        hl_msz[k] += cislo(r["P_HL"])
        if str(r.get("KANDIDAT") or "").strip() == "1":
            zvoleni_msz.add(k)
    msz = []
    for k in sorted(zvoleni_msz, key=lambda k: (nazvy_mc.get(obvod_mc.get(k[0], ""), k[0]), -hl_msz[k])):
        r = kand_msz.get(k)
        if r:
            msz.append({"obvod": nazvy_mc.get(obvod_mc.get(k[0], ""), f"obvod {k[0]}"), "meno": meno(r), "strany": strany_kandidata(r, strany), "hlasy": int(hl_msz[k])})

    # Starostovia a miestne zastupiteľstvá
    starostovia = []
    for kod_mc in mc:
        kand = [r for r in t["tab0a"] if kod(r["OBEC"]) == kod_mc]
        hl = [r for r in t["tab05"] if kod(r["OBEC"]) == kod_mc]
        v = vysledky_kandidatov(hl, kand, strany, lambda r: kod(r["PC_HL"]), lambda r: True)
        zvol = []
        kand_mz = {(kod(r["VOOBEC"]), kod(r["PC_HL"])): r for r in t["tab0b"] if kod(r["OBEC"]) == kod_mc}
        for r in t["tab08"]:
            if kod(r["OBEC"]) == kod_mc and str(r.get("KANDIDAT") or "").strip() == "1":
                kr = kand_mz.get((kod(r["VOOBEC"]), kod(r["PC_HL"])))
                if kr:
                    zvol.append({"strany": strany_kandidata(kr, strany)})
        starostovia.append({
            "kod": kod_mc, "nazov": nazvy_mc.get(kod_mc, kod_mc), "ucast": ucast(ucast_okrsky, {kod_mc}),
            "kandidati": bez_klucov(v), "miestne_zastupitelstvo": {"poslancov": len(zvol), "mandaty": mandaty(zvol)},
        })
    starostovia.sort(key=lambda x: x["nazov"])

    return {
        "primator": {"ucast": ucast(ucast_okrsky, {MESTO}), "kandidati": bez_klucov(primator), "mestske_casti": prim_mc},
        "mestske_zastupitelstvo": {"poslancov": len(msz), "mandaty": mandaty(msz), "zvoleni": msz},
        "starostovia": starostovia,
    }


def spracuj_osk(t: dict[str, list[dict]], nazvy_mc: dict[str, str]) -> dict:
    strany = {kod(r["PS"] if "PS" in r else r.get("STR")): (r.get("NPS") or r.get("NSTR") or "").strip() for r in t["tab0c"]}
    uzemie = t["tab0d"]
    kraj_obce = {kod(r["OBEC"]) for r in uzemie if kod(r["KRAJ"]) == "1"}
    ba_obce = {kod(r["OBEC"]) for r in uzemie if kod(r["KRAJ"]) == "1" and "Bratislava -" in (r.get("NOBEC") or "")}
    ba_obvody = {kod(r["VOBVOD"]) for r in uzemie if kod(r["OBEC"]) in ba_obce}
    kand = [r for r in t["tab0a"] if kod(r["KRAJ"]) == "1"]
    predseda_kraj = vysledky_kandidatov(t["tab06"], kand, strany, lambda r: kod(r["PC_HL"]), lambda r: kod(r["OBEC"]) in kraj_obce)
    predseda_ba = vysledky_kandidatov(t["tab06"], kand, strany, lambda r: kod(r["PC_HL"]), lambda r: kod(r["OBEC"]) in ba_obce)
    obec_obvod = {kod(r["OBEC"]): kod(r["VOBVOD"]) for r in uzemie}
    kand_pos = {(kod(r["VOBVOD"]), kod(r["PC_HL"])): r for r in t["tab0b"] if kod(r["VOBVOD"]) in ba_obvody}
    hl: dict[tuple, float] = defaultdict(float)
    zvol: set[tuple] = set()
    for r in t["tab09"]:
        vo = obec_obvod.get(kod(r["OBEC"]))
        if vo not in ba_obvody:
            continue
        k = (vo, kod(r["PC_HL"]))
        hl[k] += cislo(r["P_HL"])
        if str(r.get("KANDIDAT") or "").strip() == "1":
            zvol.add(k)
    nazov_obvodu = {}
    for r in uzemie:
        if kod(r["VOBVOD"]) in ba_obvody:
            nazov_obvodu.setdefault(kod(r["VOBVOD"]), []).append(nazvy_mc.get(kod(r["OBEC"]), r["NOBEC"].replace("Bratislava - ", "")))
    poslanci = [{"obvod": ", ".join(sorted(set(nazov_obvodu.get(k[0], [k[0]])))), "meno": meno(kand_pos[k]), "strany": strany_kandidata(kand_pos[k], strany), "hlasy": int(hl[k])}
                for k in sorted(zvol, key=lambda k: (k[0], -hl[k])) if k in kand_pos]
    return {
        "predseda": {
            "kraj": {"ucast": ucast(t["tab02b"], kraj_obce), "kandidati": bez_klucov(predseda_kraj)},
            "bratislava": {"ucast": ucast(t["tab02b"], ba_obce), "kandidati": [{"meno": x["meno"], "hlasy": x["hlasy"], "podiel": x["podiel"]} for x in predseda_ba]},
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
            if not ma_oso and v["id"] in stare_volby and stare_volby[v["id"]].get("stav") == "vysledky":
                zaznam = stare_volby[v["id"]]  # výsledky už máme, server dočasne nedostupný
            if zaznam.get("oso"):
                p = zaznam["oso"]["primator"]
                vit = next((k for k in p["kandidati"] if k["zvoleny"]), p["kandidati"][0] if p["kandidati"] else None)
                print(f"  primátor: {vit and vit['meno']} {vit and vit['podiel']} %, účasť {p['ucast']['ucast_pct']} %, MČ v rozdelení {len(p['mestske_casti'])}/17, "
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
