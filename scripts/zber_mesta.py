"""Krajské mestá z celoštátnych zdrojov – rovnaké ukazovatele pre všetky mestá (aj Bratislavu, kvôli porovnaniu).

Konfigurácia miest: src/mesta.json (slug, názov, kraj NUTS3, okresy).
Výstup: data/mesta/<slug>.json a data/mesta/porovnanie.json

Moduly (každý samostatne – chyba jedného nezastaví ostatné):
  obyvatelia  – ŠÚ SR DATAcube om7101rr, stav k 31. 12. (mesto alebo súčet mestských častí)
  scitanie    – ŠÚ SR STATdata, sčítanie 2021 (vek, vzdelanie, národnosť, náboženstvo, byty)
  volby       – volby.statistics.sk: NRSR 2023, EP 2024 (súčet obcí/mestských častí mesta)
  komunalne   – voľby primátora a mestského zastupiteľstva 2022 (a 2026 po zverejnení)
  praca       – ÚPSVaR: nezamestnanosť (PDU) a uchádzači v okresoch mesta, mesačne
  byty        – ŠÚ SR st3004rr: začaté a dokončené byty v okresoch mesta
  ceny        – ŠÚ SR sp3801qr: index cien bývania v kraji
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from spolocne import DATA, KOREN, s, spusti, zapis_ak_zmena

MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))
VYSTUP = DATA / "mesta"
DATACUBE = "https://data.statistics.sk/api/v2"
STATDATA = "https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/{}/download?type=CSV&lang=SK"
VOLBY_URL = "https://volby.statistics.sk/opendata"
UPSVR_JSON = "https://www.upsvr.gov.sk/statistiky/open-data/UoZ-01-zakladne-ukazovatele.json"


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").replace("–", "-")).strip()


def patri(nazov: str, mesto: str) -> bool:
    """Obec/mestská časť patrí mestu: „Košice“, „Košice - Juh“, „Košice - mestská časť Juh“, „Košice-Juh“."""
    n = norm(nazov)
    return n == mesto or n.startswith(mesto + " -") or n.startswith(mesto + "-")


def json_get(url: str, **kw) -> dict:
    r = s.get(url, timeout=180, **kw)
    r.raise_for_status()
    return r.json()


# ---------------- JSON-stat ----------------

def kategorie(dim: dict) -> list[tuple[str, str]]:
    c = dim.get("category", {})
    index, labels = c.get("index", {}), c.get("label", {}) or {}
    kody = sorted(index, key=index.get) if isinstance(index, dict) else (index or list(labels))
    return [(k, str(labels.get(k, k))) for k in kody]


def rozbal(ds: dict) -> list[dict]:
    ids, size = ds["id"], ds["size"]
    kody = [[k for k, _ in kategorie(ds["dimension"][d])] for d in ids]
    hodnoty = ds["value"]
    pocet = 1
    for x in size:
        pocet *= x
    out = []
    for i in range(pocet):
        v = hodnoty.get(str(i)) if isinstance(hodnoty, dict) else hodnoty[i]
        if v is None:
            continue
        zv, r = i, {}
        for d, sz, k in reversed(list(zip(ids, size, kody))):
            r[d] = k[zv % sz]
            zv //= sz
        r["hodnota"] = v
        out.append(r)
    return out


def dimenzie(kocka: str) -> list[tuple[str, list[tuple[str, str]]]]:
    kol = json_get(f"{DATACUBE}/collection", params={"lang": "sk"})
    polozka = next(it for it in kol["link"]["item"] if f"/dataset/{kocka}/" in it.get("href", ""))
    cesta = polozka["href"].split(f"/dataset/{kocka}/")[1].split("?")[0]
    return [(d, kategorie(json_get(f"{DATACUBE}/dimension/{kocka}/{d}", params={"lang": "sk"}))) for d in cesta.split("/")]


# ---------------- moduly ----------------

def obyvatelia() -> dict:
    dims = dimenzie("om7101rr")
    vyber, uzemie_dim, rok_dim = [], None, None
    for d, prvky in dims:
        popisy = [p for _, p in prvky]
        if len(prvky) > 2000:
            uzemie_dim = d
            vyber.append([k for k, p in prvky if any(patri(p, m["nazov"]) for m in MESTA)])
        elif all(re.fullmatch(r"\d{4}", p.strip()) for p in popisy):
            rok_dim = d
            vyber.append(["all"])
        elif len(prvky) == 1:
            vyber.append([prvky[0][0]])
        elif any("na konci obdobia" in p.lower() for p in popisy):
            vyber.append([k for k, p in prvky if "na konci obdobia" in p.lower()][:1])
        else:
            spolu = [k for k, p in prvky if p.strip().lower() in ("spolu", "úhrn", "spolu muži a ženy")]
            vyber.append(spolu[:1] or [prvky[0][0]])
    nazvy = dict(next(p for d, p in dims if d == uzemie_dim))
    out: dict[str, dict] = {}
    # po dávkach (dlhá URL)
    kody = vyber[[d for d, _ in dims].index(uzemie_dim)]
    for i in range(0, len(kody), 40):
        v = [x if d != uzemie_dim else kody[i:i + 40] for (d, _), x in zip(dims, vyber)]
        ds = json_get(f"{DATACUBE}/dataset/om7101rr/" + "/".join(",".join(k) for k in v), params={"lang": "sk"})
        for r in rozbal(ds):
            n = norm(nazvy[r[uzemie_dim]])
            for m in MESTA:
                if patri(n, m["nazov"]):
                    o = out.setdefault(m["slug"], {"mesto": {}, "casti": defaultdict(dict)})
                    if n == m["nazov"]:
                        o["mesto"][r[rok_dim]] = int(r["hodnota"])
                    else:
                        o["casti"][n][r[rok_dim]] = int(r["hodnota"])
    vysl = {}
    for slug, o in out.items():
        roky = o["mesto"]
        if not roky and o["casti"]:  # mesto len ako súčet mestských častí
            for c in o["casti"].values():
                for rok, v in c.items():
                    roky[rok] = roky.get(rok, 0) + v
        vysl[slug] = {"roky": dict(sorted(roky.items())),
                      "casti": {re.sub(r"^.*?-\s*(mestská časť\s*)?", "", c): dict(sorted(v.items())) for c, v in sorted(o["casti"].items())}}
    return vysl


# údaje za mestské časti (Bratislava, Košice – mesto je v zdrojoch len ako súčet častí); zapíšu sa do kľúča „casti“
CASTI: dict[str, dict] = defaultdict(lambda: defaultdict(dict))


def nazov_casti(n: str) -> str:
    return re.sub(r"^.*?-\s*(mestská časť\s*)?", "", norm(n))


SCITANIE = {
    "vek": ("om7803rr", "e_age"),
    "vzdelanie": ("om7809rr", "e_edu"),
    "narodnost": ("om7806rr", "e_national"),
    "nabozenstvo": ("om7805rr", "e_religion"),
    "byty_vlastnictvo": ("om7819rr", "e_ownerb"),
}


def scitanie() -> dict:
    vysl: dict[str, dict] = defaultdict(dict)
    for tema, (kocka, stlpec) in SCITANIE.items():
        r = s.get(STATDATA.format(kocka), timeout=600)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        riadky = [x for x in csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8-sig", errors="replace"))) if x.get("e_year") == "2021"]
        ostatne = [c for c in riadky[0] if c not in ("e_nuts14", "e_nuts15", "e_year", "hodnota", stlpec)]
        ma_spolu = {c: any(x[c].strip() == "Spolu" for x in riadky) for c in ostatne}
        for m in MESTA:
            sucet: dict[str, float] = defaultdict(float)
            # celé mesto, ak je v kocke; inak súčet mestských častí (nikdy oboje)
            presne = any(norm(x["e_nuts15"]) == m["nazov"] for x in riadky)
            for x in riadky:
                if not (norm(x["e_nuts15"]) == m["nazov"] if presne else patri(x["e_nuts15"], m["nazov"])):
                    continue
                if any(ma_spolu[c] and x[c].strip() != "Spolu" for c in ostatne):
                    continue
                try:
                    sucet[x[stlpec].strip()] += float(x["hodnota"] or 0)
                except ValueError:
                    pass
            if sucet:
                vysl[m["slug"]][tema] = {k: round(v) for k, v in sorted(sucet.items(), key=lambda kv: -kv[1])}
            if not presne:
                po_c: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
                for x in riadky:
                    if patri(x["e_nuts15"], m["nazov"]) and not any(ma_spolu[c] and x[c].strip() != "Spolu" for c in ostatne):
                        po_c[nazov_casti(x["e_nuts15"])][x[stlpec].strip()] += cislo(x["hodnota"])
                for c, v in po_c.items():
                    CASTI[m["slug"]].setdefault(c, {}).setdefault("scitanie", {})[tema] = {k: round(h) for k, h in sorted(v.items(), key=lambda kv: -kv[1])}
        print(f"  sčítanie {tema}: {sum(1 for v in vysl.values() if tema in v)} miest")
    return vysl


VOLBY = [
    ("nrsr2023", "Parlament 2023", "nrsr/2023/NRSR2023_SK"),
    ("ep2024", "Európsky parlament 2024", "eup/2024/EP2024_SK"),
]


def csv_url(url: str) -> list[dict]:
    r = s.get(url, timeout=300)
    r.raise_for_status()
    t = r.content.decode("utf-8-sig")
    oddel = ";" if t.split("\n", 1)[0].count(";") > t.split("\n", 1)[0].count(",") else ","
    return list(csv.DictReader(io.StringIO(t), delimiter=oddel))


def cislo(x) -> float:
    try:
        return float(str(x or 0).replace(",", ".").replace("\xa0", "").replace(" ", ""))
    except ValueError:
        return 0.0


def volby() -> dict:
    vysl: dict[str, dict] = defaultdict(dict)
    for vid, nazov, cesta in VOLBY:
        ucast = csv_url(f"{VOLBY_URL}/{cesta}_tab02d.csv")
        hlasy = csv_url(f"{VOLBY_URL}/{cesta}_tab03e.csv")
        sr = csv_url(f"{VOLBY_URL}/{cesta}_tab01.csv")[0]
        for m in MESTA:
            presne = {u["Kód obce"] for u in ucast if norm(u["Názov obce"]) == m["nazov"]}
            obce = presne or {u["Kód obce"] for u in ucast if patri(u["Názov obce"], m["nazov"])}
            if not obce:
                continue
            zap = sum(cislo(u["Počet zapísaných voličov"]) for u in ucast if u["Kód obce"] in obce)
            zuc = sum(cislo(u["Počet zúčastnených voličov"]) for u in ucast if u["Kód obce"] in obce)
            strany: dict[str, float] = defaultdict(float)
            for h in hlasy:
                if h["Kód obce"] in obce:
                    strany[h["Názov politického subjektu"].strip()] += cislo(h["Počet platných hlasov"])
            spolu = sum(strany.values()) or 1
            if not presne:
                for u in ucast:
                    if u["Kód obce"] not in obce:
                        continue
                    st: dict[str, float] = defaultdict(float)
                    for h in hlasy:
                        if h["Kód obce"] == u["Kód obce"]:
                            st[h["Názov politického subjektu"].strip()] += cislo(h["Počet platných hlasov"])
                    sp = sum(st.values()) or 1
                    z = cislo(u["Počet zapísaných voličov"])
                    CASTI[m["slug"]].setdefault(nazov_casti(u["Názov obce"]), {}).setdefault("volby", {})[vid] = {
                        "ucast": round(100 * cislo(u["Počet zúčastnených voličov"]) / z, 2) if z else None,
                        "strany": [{"nazov": n, "podiel": round(100 * h / sp, 2)} for n, h in sorted(st.items(), key=lambda x: -x[1]) if h > 0][:6]}
            vysl[m["slug"]][vid] = {
                "nazov": nazov, "ucast": round(100 * zuc / zap, 2) if zap else None, "ucast_sr": cislo(sr.get("Účasť voličov v %")),
                "strany": [{"nazov": n, "podiel": round(100 * h / spolu, 2)} for n, h in sorted(strany.items(), key=lambda x: -x[1]) if h > 0][:12],
            }
        print(f"  voľby {vid}: {sum(1 for v in vysl.values() if vid in v)} miest")
    return vysl


KOMUNALNE = [("2022", ["https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip", "https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip"]),
             ("2026", ["https://volbysr.sk/oso/files/OSO2026_SK_csv.zip", "https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"])]


def komunalne(stare: dict | None = None) -> dict:
    """Výsledky primátora a MsZ. Ročník, ktorý sa nepodarí stiahnuť (alebo ešte nemá výsledky), sa prevezme z minulého behu."""
    import zber_komunalne as zk  # pomôcky na čítanie balíka OSO (CSV/XLSX, hlavičky, mená)
    vysl: dict[str, dict] = defaultdict(dict)
    for slug, k in (stare or {}).items():
        for rok, v in (k or {}).items():
            vysl[slug][rok] = v
    for rok, urls in KOMUNALNE:
        t, _ = zk.stiahni(urls)
        if not t or not all(t.get(x) for x in ("tab0a", "tab05")):
            print(f"  komunálne {rok}: balík ešte nemá výsledky ({', '.join(sorted(t)) if t else 'balík nedostupný'})")
            if rok == "2026":  # počas sčítavania: priebežné výsledky z JSON stránky ŠÚ SR
                import volby_priebezne as vp
                for m in MESTA:
                    if m["slug"] not in vp.KODY or (vysl[m["slug"]].get(rok) or {}).get("spracovanie", {}).get("priebezne") is False and not (vysl[m["slug"]][rok]["spracovanie"].get("zdroj")):
                        continue  # konečné výsledky z balíka už máme
                    try:
                        d = vp.mesto(m["slug"])
                    except Exception as e:  # noqa: BLE001
                        print(f"::warning title=Priebežné výsledky {m['nazov']}::{e}")
                        continue
                    if d:
                        vysl[m["slug"]][rok] = d
                        print(f"  {m['nazov']} {rok}: priebežne {d['spracovanie']['pct']} %, {d['primator'][0]['meno']} {d['primator'][0]['podiel']} %")
            continue
        strany = zk.strany_mapa(t)
        for m in MESTA:
            obec = next((zk.kod(r["OBEC"]) for r in t.get("tab0d", []) if norm(r.get("NOBEC", "")) == m["nazov"]), None)
            if not obec:
                continue
            kand = [r for r in t["tab0a"] if zk.kod(r["OBEC"]) == obec]
            hl = [r for r in t["tab05"] if zk.kod(r["OBEC"]) == obec]
            zvol = {k[1] for k in zk.zvoleni(t, "tab05", lambda r: (zk.kod(r["OBEC"]), zk.kod(r["PC_HL"]))) if k[0] == obec}
            primator = zk.bez_klucov(zk.vysledky_kandidatov(hl, kand, strany, lambda r: zk.kod(r["PC_HL"]), lambda r: True, zvol or None))
            zvol_pos = {(k[1], k[2]) for k in zk.zvoleni(t, "tab08", lambda r: (zk.kod(r["OBEC"]), zk.kod(r.get("VOOBEC", "")), zk.kod(r["PC_HL"]))) if k[0] == obec}
            kand_msz = {(zk.kod(r["VOOBEC"]), zk.kod(r["PC_HL"])): r for r in t.get("tab0b", []) if zk.kod(r["OBEC"]) == obec}
            hl_msz: dict[tuple, float] = defaultdict(float)
            for r in t.get("tab08", []):
                if zk.kod(r["OBEC"]) == obec:
                    hl_msz[(zk.kod(r["VOOBEC"]), zk.kod(r["PC_HL"]))] += cislo(r["P_HL"])
            poslanci = [{"meno": zk.meno(kand_msz[k]), "strany": zk.strany_kandidata(kand_msz[k], strany), "hlasy": int(hl_msz[k])}
                        for k in sorted(zvol_pos, key=lambda k: (-hl_msz[k], k)) if k in kand_msz]
            # primátor po mestských častiach (Bratislava, Košice) – pre mapu víťazov
            mc_vysl, kontrola = zk.primator_po_mc(t, obec, m["nazov"], strany)
            if mc_vysl:
                print(f"  {m['nazov']} {rok}: primátor v {len(mc_vysl)} MČ, okrsky {kontrola}")
            vysl[m["slug"]][rok] = {
                "ucast": zk.ucast(t["tab02b"], {obec}) if "tab02b" in t else None,
                "spracovanie": zk.spracovanie(t, obec),
                **({"mestske_casti": mc_vysl} if mc_vysl else {}),
                "primator": [{"meno": x["meno"], "strany": x["strany"], "hlasy": x["hlasy"], "podiel": x["podiel"], "zvoleny": x["zvoleny"]} for x in primator],
                "zastupitelstvo": {"poslancov": len(poslanci), "mandaty": zk.mandaty(poslanci), "poslanci": poslanci},
            }
        print(f"  komunálne {rok}: {sum(1 for v in vysl.values() if rok in v)} miest")
    return vysl


def praca(stare: dict) -> dict:
    j = json_get(UPSVR_JSON)["posts"]
    obdobie = j["description"]["period"][:7]
    riadky = {norm(x["uzemie"]): x for x in j["data"]}
    vysl = {}
    for m in MESTA:
        hist = dict((stare.get(m["slug"]) or {}).get("mesacne", {}))
        okresy = {}
        for o in m["okresy"] + [m["kraj"], "Slovenská republika", "Slovensko"]:
            x = riadky.get(o) or riadky.get(f"Okres {o}")
            if x:
                okresy[o] = {"uoz": cislo(x["stav_uoz_spolu"]), "disp": cislo(x["disponibilny_pocet"]), "pdu": cislo(x["podiel_dispuoz_vpv_naopv"])}
        if okresy:
            hist[obdobie] = okresy
        vysl[m["slug"]] = {"obdobie": obdobie, "mesacne": dict(sorted(hist.items())[-36:])}
    return vysl


def byty() -> dict:
    dims = dict(dimenzie("st3004rr"))
    uz = {norm(p).replace("Okres ", ""): k for k, p in dims["nuts14"]}
    vysl = {}
    for m in MESTA:
        kody = [uz[o] for o in m["okresy"] if o in uz]
        if not kody:
            continue
        ds = json_get(f"{DATACUBE}/dataset/st3004rr/{','.join(kody)}/all/all", params={"lang": "sk"})
        roky: dict[str, dict] = defaultdict(lambda: defaultdict(float))
        for r in rozbal(ds):
            if r["st3004rr_ukaz"] in ("ZAC_BYT", "DOKONC_BYT", "ROZOST_BYT_KON"):
                roky[str(r["st3004rr_rok"])][r["st3004rr_ukaz"]] += r["hodnota"]
        vysl[m["slug"]] = {r: {k: int(v) for k, v in x.items()} for r, x in sorted(roky.items())}
    return vysl


def ceny() -> dict:
    kraje = ",".join(sorted({"SK0"} | {m["nuts3"] for m in MESTA}))
    ds = json_get(f"{DATACUBE}/dataset/sp3801qr/{kraje}/all/TOTAL/all/b_romr", params={"lang": "sk"})
    rad: dict[str, dict] = defaultdict(dict)
    for r in rozbal(ds):
        q = re.search(r"[1-4]", str(r["sp3801qr_stv"])).group(0)
        rad[r["nuts13"]][f"{r['sp3801qr_rok']}-Q{q}"] = round(r["hodnota"] - 100, 1)
    return {k: dict(sorted(v.items())) for k, v in rad.items()}


# ---------------- hlavný beh ----------------

# voliteľne len vybrané moduly, napr. `python scripts/zber_mesta.py komunalne` (volebná noc); ostatné sa prevezmú z minulého behu
LEN = set(sys.argv[1:])

def main() -> int:
    VYSTUP.mkdir(parents=True, exist_ok=True)
    stare = {m["slug"]: json.loads((VYSTUP / f"{m['slug']}.json").read_text(encoding="utf-8")) if (VYSTUP / f"{m['slug']}.json").exists() else {} for m in MESTA}
    vysledky: dict[str, dict] = {}
    chyby = []
    for nazov, fn in [("obyvatelia", obyvatelia), ("scitanie", scitanie), ("volby", volby), ("komunalne", lambda: komunalne({k: v.get("komunalne") for k, v in stare.items()})),
                      ("praca", lambda: praca({k: v.get("praca") for k, v in stare.items()})), ("byty", byty)]:
        if LEN and nazov not in LEN:
            continue
        try:
            vysledky[nazov] = fn()
            print(f"OK {nazov}")
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{nazov}: {type(e).__name__}: {e}")
            print(f"::warning title=Mestá – {nazov}::{e}")
    cenovy = None
    if not LEN or "ceny" in LEN:
        try:
            cenovy = ceny()
        except Exception as e:  # noqa: BLE001
            chyby.append(f"ceny: {e}")

    porovnanie = []
    for m in MESTA:
        d = {k: v for k, v in stare[m["slug"]].items() if k not in ("aktualizovane",)}
        for modul, v in vysledky.items():
            if m["slug"] in v:
                d[modul] = v[m["slug"]]
        if cenovy is not None:
            d["ceny"] = {"kraj": cenovy.get(m["nuts3"], {}), "sr": cenovy.get("SK0", {})}
        if CASTI.get(m["slug"]):
            casti = {c: dict(v) for c, v in (d.get("casti") or {}).items()}
            for c, v in CASTI[m["slug"]].items():
                casti.setdefault(c, {}).update(v)
            d["casti"] = dict(sorted(casti.items()))
        d["mesto"] = {k: m[k] for k in ("slug", "nazov", "kraj", "okresy")}
        d["zdroje"] = {
            "obyvatelia": "ŠÚ SR – DATAcube om7101rr", "scitanie": "ŠÚ SR – Sčítanie 2021 (STATdata)", "volby": "ŠÚ SR – volby.statistics.sk",
            "komunalne": "ŠÚ SR – volby.statistics.sk / volbysr.sk", "praca": "ÚPSVaR – mesačná štatistika", "byty": "ŠÚ SR – DATAcube st3004rr",
            "ceny": "ŠÚ SR – DATAcube sp3801qr",
        }
        zapis_ak_zmena(VYSTUP / f"{m['slug']}.json", {"aktualizovane": datetime.now().isoformat(timespec="seconds"), **d})
        roky = d.get("obyvatelia", {}).get("roky", {})
        posl = max(roky) if roky else None
        pr = (d.get("praca") or {}).get("mesacne", {})
        pr_posl = pr[max(pr)] if pr else {}
        kom = (d.get("komunalne") or {})
        kom_rok = max(kom) if kom else None
        byt = d.get("byty") or {}
        byt_10 = [byt[r].get("DOKONC_BYT", 0) for r in sorted(byt)[-11:-1]] if byt else []
        porovnanie.append({
            "slug": m["slug"], "nazov": m["nazov"],
            "obyvatelia": roky.get(posl) if posl else None, "rok": posl,
            "zmena10": round(100 * (roky[posl] / roky[str(int(posl) - 10)] - 1), 1) if posl and str(int(posl) - 10) in roky else None,
            "seniori": pct(d, "vek", "65 rokov alebo viac"), "deti": pct(d, "vek", "14 rokov alebo menej"),
            "vs": pct_vzdelanie(d), "vlastne_byty": pct_byty(d),
            "pdu": next((v["pdu"] for o, v in pr_posl.items() if o in m["okresy"]), None) if len(m["okresy"]) == 1 else
                   (round(sum(v["disp"] for o, v in pr_posl.items() if o in m["okresy"]) / max(1, sum(v["disp"] / v["pdu"] for o, v in pr_posl.items() if o in m["okresy"] and v.get("pdu"))), 2) if pr_posl else None),
            "ucast_komunalne": ((kom.get(kom_rok) or {}).get("ucast") or {}).get("ucast_pct") if kom_rok else None,
            "byty_10r": round(sum(byt_10) / len(byt_10)) if byt_10 else None,
            "ceny_kraj": list(d.get("ceny", {}).get("kraj", {}).values())[-1] if d.get("ceny", {}).get("kraj") else None,
        })
    zapis_ak_zmena(VYSTUP / "porovnanie.json", {"aktualizovane": datetime.now().isoformat(timespec="seconds"), "mesta": porovnanie})
    for p in porovnanie:
        print(p)
    if len(chyby) >= 4:
        raise RuntimeError("; ".join(chyby))
    for c in chyby:
        print("CHYBA", c)
    return 0


def pct(d: dict, tema: str, kat: str) -> float | None:
    t = (d.get("scitanie") or {}).get(tema)
    if not t:
        return None
    spolu = t.get("Spolu") or sum(v for k, v in t.items() if k != "Spolu")
    return round(100 * t.get(kat, 0) / spolu, 1) if spolu else None


def pct_vzdelanie(d: dict) -> float | None:
    t = (d.get("scitanie") or {}).get("vzdelanie")
    if not t:
        return None
    spolu = t.get("Spolu") or sum(v for k, v in t.items() if k != "Spolu")
    vs = sum(v for k, v in t.items() if re.search(r"vysokoškolsk|doktorandsk|magistersk|bakalársk|inžiniersk", k, re.I))
    return round(100 * vs / spolu, 1) if spolu else None


def pct_byty(d: dict) -> float | None:
    t = (d.get("scitanie") or {}).get("byty_vlastnictvo")
    if not t:
        return None
    spolu = t.get("Spolu") or sum(v for k, v in t.items() if k != "Spolu")
    vl = sum(v for k, v in t.items() if re.match(r"vlastný byt|byt vo vlastnom", k))
    return round(100 * vl / spolu, 1) if spolu else None


if __name__ == "__main__":
    spusti(main, "Zber krajských miest")
