"""Ďalšie údaje pre všetky obce SR: nezamestnanosť, komunálny odpad, školy.

  1. Nezamestnanosť – ÚPSVaR, Mesačná štatistika o počte a štruktúre uchádzačov o zamestnanie podľa obcí
     (upsvr.gov.sk → Štatistiky → Mesačné štatistiky miest a obcí), tabuľka 1: uchádzači (UoZ), disponibilní UoZ,
     obyvatelia v produktívnom veku (OPV), PDU = podiel disponibilných UoZ na OPV. Posledných 13 mesiacov.
  2. Komunálny odpad – ŠÚ SR STATdata zp3804rr „Množstvo komunálneho odpadu podľa druhov odpadu za obce“
     (filtrované otvorené dáta, ukazovateľ „Komunálny odpad z obcí“). Podiel triedeného odpadu je odhad:
     1 − (zmesový 20 03 01 + objemný 20 03 07 + uličné smetie 20 03 03) / všetok komunálny odpad obce.
     Nie je to úradná „úroveň vytriedenia“ podľa vyhlášky (tú si obec počíta sama a údaje sa nezverejňujú centrálne).
  3. Školy – MŠVVaM SR, Digitálna mapa škôl (mapaskol.iedu.sk): školy a školské zariadenia s počtom žiakov,
     priradené k obci podľa názvu a polohy.

Výstupy: data/obce/nezamestnanost.json, data/obce/odpad.json, data/obce/skoly.json
Každý modul beží samostatne – chyba jedného nezastaví ostatné.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import sys
import unicodedata
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

import openpyxl

from spolocne import DATA, s, spusti, zapis_ak_zmena

OBCE = json.loads((DATA / "obce" / "zoznam.json").read_text(encoding="utf-8"))["obce"]


def bez_dia(t: str) -> str:
    t = unicodedata.normalize("NFD", str(t or ""))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def kluc(t: str) -> str:
    """Porovnávací kľúč názvu: bez diakritiky, malé písmená, spojovníky bez medzier."""
    t = re.sub(r"\s*-\s*", "-", bez_dia(t).lower())
    return re.sub(r"\s+", " ", t).strip()


PODLA_OKRESU: dict[tuple[str, str], str] = {(kluc(o["okres"]), kluc(o["nazov"])): o["kod"] for o in OBCE}
PODLA_NAZVU: dict[str, list[str]] = defaultdict(list)
for _o in OBCE:
    PODLA_NAZVU[kluc(_o["nazov"])].append(_o["kod"])


def najdi_obec(nazov: str, okres: str | None = None) -> str | None:
    k = kluc(nazov)
    if okres and (kluc(okres), k) in PODLA_OKRESU:
        return PODLA_OKRESU[(kluc(okres), k)]
    kand = PODLA_NAZVU.get(k, [])
    if len(kand) == 1:
        return kand[0]
    if okres and "." in nazov:  # skrátené názvy v ÚPSVaR („Pod.Biskup.“)
        vzor = re.compile("^" + re.escape(k).replace(r"\.", r"[^ ]*\.?\s*") + ".*$")
        kand = [kod for (ok, n), kod in PODLA_OKRESU.items() if ok == kluc(okres) and vzor.match(n)]
        if len(kand) == 1:
            return kand[0]
    return None


def median(xs: list[float]) -> float | None:
    xs = sorted(x for x in xs if x is not None)
    if len(xs) < 3:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


# ---------------- 1. nezamestnanosť (ÚPSVaR) ----------------

UPSVR = "https://www.upsvr.gov.sk"
UPSVR_OBCE = UPSVR + "/statistiky/mesacne-statistiky-miest-a-obci.html?page_id=1009850"
MESIACOV = 13


def upsvr_subory() -> list[tuple[str, str]]:
    """[(„2026-09“, url), …] od najnovšieho."""
    r = s.get(UPSVR_OBCE, timeout=60)
    r.raise_for_status()
    roky = sorted(set(re.findall(r'href="(https://www\.upsvr\.gov\.sk/statistiky/mesacne-statistiky-miest-a-obci/(\d{4})\.html\?page_id=\d+)"', r.text)),
                  key=lambda x: x[1], reverse=True)
    out: dict[str, str] = {}
    for url, rok in roky[:3]:
        t = s.get(url, timeout=60).text
        for u in re.findall(r'href="([^"]*mesta_a_o[^"]*\.xlsx)"', t):
            u = u if u.startswith("http") else UPSVR + u
            m = re.search(r"_(\d{2})(\d{2})(?:_\d)?\.xlsx$", u) or re.search(r"_(\d{2})_(20\d{2})(?:_\d)?\.xlsx$", u)
            if not m:
                continue
            a, b = m.groups()
            mesiac = f"20{a}-{b}" if len(b) == 2 and len(a) == 2 and not b.startswith("20") else f"{b}-{a}"
            if mesiac.startswith(rok):
                out.setdefault(mesiac, u)
        if len(out) >= MESIACOV:
            break
    return sorted(out.items(), reverse=True)[:MESIACOV]


def cislo(x) -> float | None:
    if x is None or isinstance(x, str) and not re.match(r"^-?[\d\s.,]+$", x.strip()):
        return None
    try:
        return float(str(x).replace("\xa0", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def upsvr_mesiac(url: str) -> dict[str, dict]:
    r = s.get(url, timeout=180)
    if r.status_code != 200 or r.content[:2] != b"PK":
        raise RuntimeError(f"ÚPSVaR {url}: {r.status_code}")
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    ws = wb[next(n for n in wb.sheetnames if n.lower().startswith("tab01"))]
    out, okres, nenajdene = {}, None, []
    for row in ws.iter_rows(values_only=True):
        row = list(row)
        if len(row) < 11 or not isinstance(row[1], str):
            continue
        if isinstance(row[0], str) and row[0].strip() and not row[0].startswith(("Okres", "Ústredie", "Mesačná")):
            okres = row[0].strip()
        vals = [cislo(x) for x in row[2:11]]
        if vals[0] is None or okres is None:
            continue
        nazov = row[1].strip()
        kod = najdi_obec(nazov, okres)
        if not kod:
            nenajdene.append(f"{nazov} ({okres})")
            continue
        uoz, _zp, _ml, absol, _ned, opv, disp, pu, pdu = vals
        out[kod] = {"uoz": int(uoz), "disp": int(disp or 0), "opv": int(opv or 0), "abs": int(absol or 0), "pdu": pdu, "pu": pu}
    if len(out) < 2500:
        raise RuntimeError(f"ÚPSVaR: priradených len {len(out)} obcí; napr. {nenajdene[:8]}")
    if nenajdene and not getattr(upsvr_mesiac, "vypisane", False):
        upsvr_mesiac.vypisane = True  # type: ignore[attr-defined]
        print(f"  nepriradené ({len(nenajdene)}): {', '.join(nenajdene[:12])}")
    return out


def nezamestnanost() -> None:
    subory = upsvr_subory()
    if not subory:
        raise RuntimeError("ÚPSVaR: nenašiel sa žiadny mesačný súbor obcí")
    mesiace: dict[str, dict] = {}
    for mesiac, url in subory:
        try:
            mesiace[mesiac] = upsvr_mesiac(url)
            print(f"Nezamestnanosť {mesiac}: {len(mesiace[mesiac])} obcí")
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Nezamestnanosť obcí::{mesiac}: {e}")
    if not mesiace:
        raise RuntimeError("ÚPSVaR: žiadny mesiac sa nepodarilo načítať")
    posledny = max(mesiace)
    akt = mesiace[posledny]
    okr = {o["kod"]: o["okres"] for o in OBCE}
    # okresy a SR – podiel súčtov (rovnako ako ÚPSVaR počíta PDU za okres)
    sucty: dict[str, list] = defaultdict(lambda: [0, 0])
    for kod, v in akt.items():
        sucty[okr[kod]][0] += v["disp"]
        sucty[okr[kod]][1] += v["opv"]
    okresy = {o: round(100 * d / n, 2) for o, (d, n) in sucty.items() if n}
    sr = [sum(v["disp"] for v in akt.values()), sum(v["opv"] for v in akt.values())]
    obce = {}
    for kod, v in sorted(akt.items()):
        rad = {m: mesiace[m][kod]["pdu"] for m in sorted(mesiace) if kod in mesiace[m] and mesiace[m][kod]["pdu"] is not None}
        obce[kod] = {**{k: v[k] for k in ("uoz", "disp", "opv", "abs", "pdu")}, "rad": rad}
    zapis_ak_zmena(DATA / "obce" / "nezamestnanost.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "mesiac": posledny,
        "sr": round(100 * sr[0] / sr[1], 2) if sr[1] else None, "okresy": dict(sorted(okresy.items())),
        "zdroj": {"nazov": "ÚPSVaR – Mesačná štatistika o počte a štruktúre uchádzačov o zamestnanie podľa obcí", "url": UPSVR_OBCE},
        "obce": obce}, kompaktne=True)
    print(f"Nezamestnanosť: {posledny}, {len(obce)} obcí, SR PDU {round(100 * sr[0] / sr[1], 2)} %")


# ---------------- 2. komunálny odpad (ŠÚ SR) ----------------

ODPAD_URL = ("https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/zp3804rr"
             "/rows/e_nuts15,ASC,all~e_ewc,ASC,all/columns/e_year,ASC,all/context/e_indic,ASC,U_ZP_0091~e_unit,ASC,all")
NETRIEDENE = ("200301", "200307", "200303")  # zmesový, objemný, uličné smetie


def odpad() -> None:
    r = s.get(ODPAD_URL, params={"type": "CSV", "lang": "SK"}, timeout=900)
    r.raise_for_status()
    c = r.content
    if c[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(c))
        c = z.read(z.namelist()[0])
    data: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"spolu": 0.0, "zmes": 0.0, "netr": 0.0, "bio": 0.0}))
    nenajdene = set()
    for x in csv.DictReader(io.StringIO(c.decode("utf-8-sig", "replace"))):
        v = cislo(x.get("hodnota"))
        if v is None:
            continue
        n15 = x["e_nuts15"]
        m = re.match(r"^(.*?),\s*okres\s+(.*)$", n15)
        kod = najdi_obec(m.group(1), m.group(2)) if m else najdi_obec(n15)
        if not kod:
            nenajdene.add(n15)
            continue
        kat = x["e_ewc"][:6]
        d = data[kod][x["e_year"]]
        d["spolu"] += v
        if kat == "200301":
            d["zmes"] += v
        if kat in NETRIEDENE:
            d["netr"] += v
        if kat in ("200201", "200108"):
            d["bio"] += v
    if len(data) < 2500:
        raise RuntimeError(f"Odpad: priradených len {len(data)} obcí (napr. {sorted(nenajdene)[:8]})")
    print(f"Odpad: {len(data)} obcí; nepriradené územia {len(nenajdene)} (kraje, okresy, MČ …)")
    ob = {o["kod"]: o.get("obyvatelia") for o in OBCE}
    okr = {o["kod"]: o["okres"] for o in OBCE}
    obce = {}
    for kod, roky in data.items():
        out = {}
        for rok, d in sorted(roky.items()):
            if d["spolu"] <= 0:
                continue
            e = {"t": round(d["spolu"], 1), "triedene": round(100 * (1 - d["netr"] / d["spolu"]), 1), "bio": round(d["bio"], 1)}
            if ob.get(kod):
                e["kg"] = round(1000 * d["spolu"] / ob[kod])
                e["kg_zmes"] = round(1000 * d["zmes"] / ob[kod])
            out[rok] = e
        if out:
            obce[kod] = out
    rok = max(r for v in obce.values() for r in v)
    okresy = {}
    po_okr: dict[str, list] = defaultdict(list)
    for kod, v in obce.items():
        if rok in v:
            po_okr[okr[kod]].append(v[rok])
    for o, xs in po_okr.items():
        okresy[o] = {"triedene": median([x["triedene"] for x in xs]), "kg_zmes": median([x.get("kg_zmes") for x in xs])}
    sr_x = [v[rok] for v in obce.values() if rok in v]
    zapis_ak_zmena(DATA / "obce" / "odpad.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rok": rok,
        "sr": {"triedene": median([x["triedene"] for x in sr_x]), "kg_zmes": median([x.get("kg_zmes") for x in sr_x])},
        "okresy": dict(sorted(okresy.items())),
        "zdroj": {"nazov": "ŠÚ SR – Množstvo komunálneho odpadu podľa druhov odpadu za obce (zp3804rr)", "url": "https://statdata.statistics.sk"},
        "obce": dict(sorted(obce.items()))}, kompaktne=True)
    print(f"Odpad {rok}: {len(obce)} obcí, medián podielu triedeného {median([x['triedene'] for x in sr_x])} %")


# ---------------- 3. školy (MŠVVaM SR) ----------------

# typ podľa názvu v mape škôl – súčasti „ZŠ s MŠ“ sú samostatné riadky („ZŠ s MŠ - MŠ - Obec“ = materská škola)
TYP_SKOLY = [
    (None, r"jed\.|jedáleň|jedalen|\bŠJ\b|výdaj|ŠKD|[Šš]kol\.\s*kl|klub|intern|poraden|CPP|Jazyková"),
    ("cvc", r"CVČ|voľného času"),
    ("ms", r"(^|\s-\s)(MŠ|SMŠ|CMŠ)\b|^Materská|^Mater\."),
    ("zus", r"ZUŠ|umeleck\w* škola\b(?!.*priem)"),
    ("spec", r"Špec|ŠZŠ|Diag|Liečeb|Reedukač|Odbor\.\s*učil|Prakt|mim\.\s*nad|\bOU\b"),
    ("zs", r"\bZŠ|Základná|ZŠsMŠ"),
    ("ss", r"[Gg]ym|SOŠ|SPŠ|\bOA\b|\bHA\b|SZŠ|[Kk]onz|lýceum|ŠUP|umeleckého priem|SŠ|SUŠ|Tanečn|Bilingv|CSOŠ|akadém|stredn|Spojená"),
]


def typ_skoly(nazov: str) -> str | None:
    for t, r in TYP_SKOLY:
        if re.search(r, nazov):
            return t
    return None


def skoly() -> None:
    from zber_skoly_iedu import TYPY, URL_MAPA, citaj, num
    typ = typ_skoly
    riadky = citaj(URL_MAPA)
    if len(riadky) < 5000:
        raise RuntimeError(f"Mapa škôl: málo riadkov ({len(riadky)})")
    pol = {o["kod"]: o.get("poloha") for o in OBCE}
    po_obci: dict[str, list] = defaultdict(list)
    nenajdene = 0
    for x in riadky:
        t = typ(x.get("Názov") or "")
        if not t:
            continue
        nazov_obce = re.sub(r"^\d{3}\s?\d{2}\s+", "", (x.get("Obec") or "").strip())
        nazov_obce = re.sub(r"\s*-\s*.*$", "", nazov_obce) if not PODLA_NAZVU.get(kluc(nazov_obce)) else nazov_obce
        kand = PODLA_NAZVU.get(kluc(nazov_obce), [])
        lat, lon = num(x.get("GPS1")), num(x.get("GPS2"))
        if len(kand) > 1 and lat and lon:  # rovnaký názov vo viacerých okresoch – najbližšia obec
            kand = [min(kand, key=lambda k: math.dist(pol[k] or (0, 0), (lat, lon)))]
        if len(kand) != 1:
            nenajdene += 1
            continue
        ziaci = num(x.get("Počet žiakov"))
        po_obci[kand[0]].append([re.sub(r"\s+", " ", x["Názov"]).strip(), t, int(ziaci) if ziaci else None])
    if len(po_obci) < 1500:
        raise RuntimeError(f"Školy: priradené len k {len(po_obci)} obciam")
    obce = {}
    for kod, zz in sorted(po_obci.items()):
        typy: dict[str, list] = defaultdict(lambda: [0, 0])
        for _, t, z in zz:
            typy[t][0] += 1
            typy[t][1] += z or 0
        poradie = list(TYPY)
        obce[kod] = {"typy": {t: typy[t] for t in poradie if t in typy},
                     "zoznam": sorted(zz, key=lambda x: (poradie.index(x[1]) if x[1] in poradie else 9, -(x[2] or 0)))[:15]}
    zapis_ak_zmena(DATA / "obce" / "skoly.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "typy": TYPY,
        "zdroj": {"nazov": "MŠVVaM SR – Digitálna mapa škôl", "url": "https://mapaskol.iedu.sk"},
        "obce": obce}, kompaktne=True)
    print(f"Školy: {len(obce)} obcí so školou, nepriradených škôl {nenajdene}")


def main() -> int:
    moduly = {"nezamestnanost": nezamestnanost, "odpad": odpad, "skoly": skoly}
    vyber = sys.argv[1:] or list(moduly)
    chyby = 0
    for m in vyber:
        try:
            moduly[m]()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=Obce – {m}::{e}")
    if chyby == len(vyber):
        raise RuntimeError("žiadny modul neprebehol")
    return 0


if __name__ == "__main__":
    spusti(main, "Nezamestnanosť, odpad a školy v obciach")
