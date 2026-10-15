"""Faktúry, objednávky a zmluvy magistrátu a mestských organizácií (OLO, Marianum, MIB) – súhrny.

Zdroj: data.bratislava.sk (CC BY 4.0). Datasety sú veľké (magistrát má 142 tisíc faktúr od 2011),
preto zverejňujeme súhrny: počty a sumy podľa rokov, najväčší dodávatelia, najväčšie položky
za posledných 12 mesiacov a pri faktúrach magistrátu priemerný čas úhrady.

GDPR: vynechávame dodávateľov bez IČO a označených ako fyzická osoba; nezverejňujeme mená
osôb, ktoré objednávky podpísali.

Výstup: data/faktury-bratislava.json
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import median

from spolocne import DATA, s, spusti, zapis_ak_zmena

ITEM = "https://www.arcgis.com/sharing/rest/content/items/{}"
DATASETY = [  # (prefix ID, organizácia, typ)
    ("7f719a61", "Magistrát", "faktúry"), ("e3a9501c", "Magistrát", "objednávky"),
    ("6b2c7034", "OLO", "faktúry"), ("cb90eb53", "OLO", "objednávky"), ("a5068dd4", "OLO", "zmluvy"),
    ("bd9ee647", "Marianum", "faktúry"), ("81abdb95", "Marianum", "objednávky"), ("b50effaa", "Marianum", "zmluvy"),
    ("8cb2a28c", "Metropolitný inštitút Bratislavy", "faktúry"),
]
VZORY = {
    "dodavatel": r"(názov_dodávateľa|dodávateľ_+názov|dodávateľ__meno|^dodávateľ$)",
    "ico": r"(ičo_dodávateľa|dodávateľ_+ičo|^ičo$)",
    "fo": r"dodávateľ_+fo",
    "suma": r"(celková_suma|suma_v|fakturovaná_suma|^suma$|hodnota_objednávky|celková_hodnota|hodnota_zmluvy|finančný_rámec|^cena$)",
    "datum": r"(dátum_doručenia|datum_objednavky|dátum_vyhotovenia|dátum_vystavenia|dátum_podpísania|dátum_schválenia)",
    "uhrada": r"dátum_úhrady",
    "popis": r"(popis_fakturovaného|predmet|^názov_zmluvy$|^popis$)",
}


# pri datasetoch bez IČO berieme len dodávateľov s právnou formou v názve (fyzické osoby vynechávame)
PRAVNA_FORMA = re.compile(r"s\.\s?r\.\s?o|spol\.|a\.\s?s\.|k\.\s?s\.|v\.\s?o\.\s?s|n\.\s?o\.|o\.\s?z\.|z\.\s?p\.\s?o|š\.\s?p\.|gmbh|ltd|inc\.|mesto|mestská časť|hlavné mesto|ministerstvo|úrad|univerzit|ústav|inštitút|nadácia|fond|cirk|zväz|združenie|komora|banka|poisťov|slovenská|slovenský|podnik|agentúra|správa", re.I)


def plne_id(prefix: str) -> str | None:
    for p in json.loads((DATA / "katalog-bratislava.json").read_text(encoding="utf-8"))["datasety"]:
        if p["id"].startswith(prefix):
            return p["id"]
    return None


def vrstva(item: str) -> str:
    url = s.get(ITEM.format(item), params={"f": "json"}, timeout=60).json()["url"].rstrip("/")
    return url if url[-1].isdigit() else url + "/0"


def riadky(url: str, polia: list[str]) -> list[dict]:
    vysl, offset = [], 0
    while True:
        r = s.get(url + "/query", params={"where": "1=1", "outFields": ",".join(polia), "returnGeometry": "false",
                                          "resultOffset": offset, "resultRecordCount": 2000, "f": "json"}, timeout=240).json()
        if "error" in r:
            raise RuntimeError(r["error"])
        f = [x["attributes"] for x in r.get("features", [])]
        vysl += f
        if len(f) < 2000 and not r.get("exceededTransferLimit"):
            return vysl
        offset += len(f)


def suma(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    t = re.sub(r"[^\d,.\-]", "", str(v or ""))
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def den(v) -> date | None:
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, timezone.utc).date()
    t = str(v or "").strip()
    for vzor, fmt in ((r"^\d{4}-\d{2}-\d{2}", "%Y-%m-%d"), (r"^\d{1,2}\.\s?\d{1,2}\.\s?\d{4}", None)):
        m = re.match(vzor, t)
        if m:
            if fmt:
                return datetime.strptime(m.group(0), fmt).date()
            d, mo, r = re.findall(r"\d+", m.group(0))[:3]
            try:
                return date(int(r), int(mo), int(d))
            except ValueError:
                return None
    return None


def spracuj(item: str, org: str, typ: str) -> dict:
    url = vrstva(item)
    meta = s.get(url, params={"f": "json"}, timeout=60).json()
    mena = [f["name"] for f in meta.get("fields", [])]
    stlpec = {k: next((m for m in mena if re.search(v, m, re.I)), None) for k, v in VZORY.items()}
    if not stlpec["suma"] or not stlpec["dodavatel"]:
        raise RuntimeError(f"{org} {typ}: chýba stĺpec sumy alebo dodávateľa ({mena})")
    data = riadky(url, [c for c in stlpec.values() if c])
    po_rokoch: dict[int, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0})
    dodavatelia: dict[tuple, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0})
    polozky, dni_uhrady, vynechane = [], defaultdict(list), 0
    dnes = date.today()
    for r in data:
        meno_dod = re.sub(r"\s+", " ", str(r.get(stlpec["dodavatel"]) or "")).strip()
        if stlpec["ico"]:
            ico = re.sub(r"\D", "", str(r.get(stlpec["ico"]) or ""))
            fo = str(r.get(stlpec["fo"]) or "").strip().lower() in ("áno", "ano", "a", "1", "true", "x") if stlpec["fo"] else False
            if not ico or fo or len(ico) < 6:
                vynechane += 1
                continue
        else:
            if not PRAVNA_FORMA.search(meno_dod):
                vynechane += 1
                continue
            ico = ""
        hodnota, d = suma(r.get(stlpec["suma"])), den(r.get(stlpec["datum"])) if stlpec["datum"] else None
        if hodnota is None or d is None or not (2005 <= d.year <= dnes.year):
            continue
        meno = re.sub(r"\s+", " ", str(r.get(stlpec["dodavatel"]) or "")).strip()
        po_rokoch[d.year]["pocet"] += 1
        po_rokoch[d.year]["suma"] += hodnota
        if d.year >= dnes.year - 2:
            dod = dodavatelia[(ico or meno_dod.lower(), )]
            dod["nazov"] = meno
            dod["pocet"] += 1
            dod["suma"] += hodnota
        if d >= dnes - timedelta(days=365):
            polozky.append({"datum": d.isoformat(), "dodavatel": meno, "ico": ico, "suma": round(hodnota, 2),
                            "popis": re.sub(r"\s+", " ", str(r.get(stlpec["popis"]) or "")).strip()[:200] if stlpec["popis"] else ""})
        if stlpec["uhrada"]:
            u = den(r.get(stlpec["uhrada"]))
            if u and u >= d and (u - d).days < 400:
                dni_uhrady[d.year].append((u - d).days)
    if not po_rokoch:
        raise RuntimeError(f"{org} {typ}: žiadne použiteľné riadky")
    return {
        "organizacia": org, "typ": typ, "zdroj": f"https://data.bratislava.sk/datasets/{item}", "zaznamov": len(data), "vynechane_bez_ico": vynechane,
        "roky": {str(k): {"pocet": v["pocet"], "suma": round(v["suma"])} for k, v in sorted(po_rokoch.items())},
        "dodavatelia_posledne_3_roky": sorted(({"ico": k[0], "nazov": v["nazov"], "pocet": v["pocet"], "suma": round(v["suma"])} for k, v in dodavatelia.items()),
                                              key=lambda x: -x["suma"])[:20],
        "najvacsie_12_mesiacov": sorted(polozky, key=lambda x: -x["suma"])[:15],
        "median_dni_uhrady": {str(k): median(v) for k, v in sorted(dni_uhrady.items()) if len(v) > 20} or None,
    }


def main() -> int:
    vysledky, chyby = [], []
    for prefix, org, typ in DATASETY:
        item = plne_id(prefix)
        if not item:
            chyby.append(f"{org} {typ}: nie je v inventári")
            continue
        try:
            v = spracuj(item, org, typ)
            vysledky.append(v)
            print(f"{org} {typ}: {v['zaznamov']} záznamov, rokov {len(v['roky'])}, vynechané bez IČO/FO {v['vynechane_bez_ico']}")
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{org} {typ}: {e}")
            print(f"CHYBA {org} {typ}: {e}")
    if len(vysledky) < 4:
        raise RuntimeError("; ".join(chyby))
    zapis_ak_zmena(DATA / "faktury-bratislava.json", {"datasety": vysledky, "chyby": chyby,
                                                      "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return 0


if __name__ == "__main__":
    spusti(main, "Zber faktúr a objednávok")
