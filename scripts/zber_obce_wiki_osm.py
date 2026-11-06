"""Obce z Wikidata a OpenStreetMap.

  wiki – Wikidata: prvá písomná zmienka (P1249) a nadmorská výška (P2044); obec podľa LAU kódu (P782, posledných 6 číslic = kód obce).
  osm  – OpenStreetMap (Overpass): počet obchodov s potravinami, reštaurácií/kaviarní/pohostinstiev, detských ihrísk a nabíjacích
         staníc v hraniciach obce (admin_level 8 s tagom ref = kód obce; Bratislava a Košice cez svoje okresy).
         Úplnosť OSM sa medzi obcami líši – na webe s poznámkou.

Výstupy data/obce/wiki.json, data/obce/osm.json.
"""

from __future__ import annotations

import re
import sys
import time
from datetime import datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE

KODY = {o["kod"] for o in OBCE}
MESTA = {o["nazov"]: o["kod"] for o in OBCE if o["nazov"] in ("Bratislava", "Košice")}
UA = {"User-Agent": "mestovcislach.sk/1.0 (info@mestovcislach.sk)"}


def zapis(nazov: str, obsah: dict) -> None:
    zapis_ak_zmena(DATA / "obce" / f"{nazov}.json", {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), **obsah}, kompaktne=True)


def wiki() -> None:
    q = """SELECT ?lau ?zm ?zmp ?vys WHERE { ?o wdt:P17 wd:Q214 ; wdt:P782 ?lau .
      OPTIONAL { ?o p:P1249/psv:P1249 [ wikibase:timeValue ?zm ; wikibase:timePrecision ?zmp ] }
      OPTIONAL { ?o wdt:P2044 ?vys } }"""
    r = s.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, headers=UA, timeout=300)
    r.raise_for_status()
    obce: dict[str, list] = {}
    for b in r.json()["results"]["bindings"]:
        kod = b["lau"]["value"][-6:]
        if kod not in KODY:
            continue
        o = obce.setdefault(kod, [None, None])
        if "zm" in b and int(b.get("zmp", {}).get("value", 9)) >= 9:  # presnosť aspoň na rok
            m = re.match(r"^(-?\d+)", b["zm"]["value"])
            if m:
                rok = int(m.group(1))
                if 800 <= rok <= 2025:
                    o[0] = rok if o[0] is None else min(o[0], rok)
        if "vys" in b:
            try:
                v = round(float(b["vys"]["value"]))
                if 90 <= v <= 1500:
                    o[1] = v if o[1] is None else o[1]
            except ValueError:
                pass
    obce = {k: v for k, v in obce.items() if v[0] or v[1]}
    print(f"Wikidata: {len(obce)} obcí, zmienka {sum(1 for v in obce.values() if v[0])}, výška {sum(1 for v in obce.values() if v[1])}")
    if len(obce) < 2500:
        raise RuntimeError(f"Wikidata: len {len(obce)} obcí")
    zapis("wiki", {"zdroj": {"nazov": "Wikidata – prvá písomná zmienka, nadmorská výška", "url": "https://www.wikidata.org"},
                   "obce": dict(sorted(obce.items()))})


OSM_KAT = [  # (kľúč, filter)
    ("potraviny", 'nwr[shop~"^(supermarket|convenience|greengrocer|butcher|bakery)$"]'),
    ("jedlo", 'nwr[amenity~"^(restaurant|pub|cafe|fast_food|bar)$"]'),
    ("ihriska", "nwr[leisure=playground]"),
    ("nabijacky", "nwr[amenity=charging_station]"),
]


def _overpass(q: str) -> list[dict]:
    for pokus in range(4):
        r = s.post("https://overpass-api.de/api/interpreter", data={"data": q}, headers=UA, timeout=1900)
        if r.status_code in (429, 502, 503, 504):
            time.sleep(60 * (pokus + 1))
            continue
        r.raise_for_status()
        return r.json().get("elements", [])
    raise RuntimeError("Overpass neodpovedá")


def _pocty(oblasti: str) -> list[tuple[dict, list[int]]]:
    """Pre každú oblasť (tags) počty OSM_KAT – výstup foreach: area tags, potom 1 count na kategóriu."""
    telo = "".join(f"{f}(area.a);out count;" for _, f in OSM_KAT)
    q = (f'[out:json][timeout:1800];area["ISO3166-1"="SK"][admin_level=2]->.sk;{oblasti}->.obl;'
         f"foreach.obl->.a(.a out tags;{telo});")
    el = _overpass(q)
    out, akt = [], None
    for e in el:
        if e.get("type") == "area":
            akt = (e.get("tags", {}), [])
            out.append(akt)
        elif e.get("type") == "count" and akt is not None:
            akt[1].append(int(e.get("tags", {}).get("total", 0)))
    return out


def osm() -> None:
    obce: dict[str, list[int]] = {}
    for tags, c in _pocty('area(area.sk)[boundary=administrative][admin_level=8][ref]'):
        if tags.get("ref") in KODY and len(c) == len(OSM_KAT):
            obce[tags["ref"]] = c
    mesta: dict[str, list[int]] = {}
    for tags, c in _pocty('area(area.sk)[boundary=administrative][name~"^[Oo]kres (Bratislava|Košice) [IV]+$"]'):
        m = re.search(r"(Bratislava|Košice)", tags.get("name", ""))
        kod = MESTA.get(m.group(1)) if m else None
        if kod and len(c) == len(OSM_KAT):
            mesta[kod] = [a + b for a, b in zip(mesta.get(kod, [0] * len(OSM_KAT)), c)]
    obce.update(mesta)  # mesto = súčet jeho okresov (mestské časti majú vlastné kódy)
    print(f"OSM: {len(obce)} obcí; spolu {dict(zip([k for k, _ in OSM_KAT], [sum(v[i] for v in obce.values()) for i in range(len(OSM_KAT))]))}")
    if len(obce) < 2500:
        raise RuntimeError(f"OSM: len {len(obce)} obcí")
    zapis("osm", {"kategorie": [k for k, _ in OSM_KAT], "datum": datetime.now(timezone.utc).date().isoformat(),
                  "zdroj": {"nazov": "© prispievatelia OpenStreetMap (ODbL)", "url": "https://www.openstreetmap.org/copyright"},
                  "obce": dict(sorted(obce.items()))})


MODULY = {"wiki": wiki, "osm": osm}


def main() -> int:
    vyber = sys.argv[1:] or list(MODULY)
    chyby = 0
    for m in vyber:
        try:
            MODULY[m]()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=Obce Wikidata/OSM – {m}::{e}")
    if chyby == len(vyber):
        raise RuntimeError("žiadny modul neprebehol")
    return 0


if __name__ == "__main__":
    spusti(main, "Obce – Wikidata a OpenStreetMap")
