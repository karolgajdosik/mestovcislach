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


OSM_KAT = [  # (kľúč, test na tagy)
    ("potraviny", lambda t: t.get("shop") in ("supermarket", "convenience", "greengrocer", "butcher", "bakery")),
    ("jedlo", lambda t: t.get("amenity") in ("restaurant", "pub", "cafe", "fast_food", "bar")),
    ("ihriska", lambda t: t.get("leisure") == "playground"),
    ("nabijacky", lambda t: t.get("amenity") == "charging_station"),
]
SK = 'area["ISO3166-1"="SK"][admin_level=2]->.sk;'


def _overpass(q: str) -> list[dict]:
    chyba = None
    for pokus in range(4):
        try:
            r = s.post("https://overpass-api.de/api/interpreter", data={"data": q}, headers=UA, timeout=1000)
            if r.status_code == 200:
                return r.json().get("elements", [])
            chyba = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            chyba = str(e)
        print(f"  Overpass: {chyba}")
        time.sleep(60 * (pokus + 1))
    raise RuntimeError(f"Overpass: {chyba}")


def _hranice() -> dict[str, object]:
    """kód obce -> polygón (shapely). Obce = admin_level 8 s ref; Bratislava a Košice = zjednotenie ich okresov."""
    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union
    el = _overpass(f'[out:json][timeout:900];{SK}(rel(area.sk)[boundary=administrative][admin_level=8][ref];'
                   'rel(area.sk)[boundary=administrative][admin_level=6][name~"^[Oo]kres (Bratislava|Košice) [IV]+$"];);out geom;')
    out: dict[str, list] = {}
    for e in el:
        t = e.get("tags", {})
        kod = t.get("ref") if t.get("admin_level") == "8" else None
        if t.get("admin_level") == "6":
            m = re.search(r"(Bratislava|Košice)", t.get("name", ""))
            kod = MESTA.get(m.group(1)) if m else None
        if kod not in KODY:
            continue
        ciary = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in e.get("members", [])
                 if m.get("type") == "way" and m.get("geometry") and len(m["geometry"]) > 1]
        if not ciary:
            continue
        g = unary_union(list(polygonize(unary_union(ciary))))
        if not g.is_empty:
            out.setdefault(kod, []).append(g)
    return {k: unary_union(v) if len(v) > 1 else v[0] for k, v in out.items()}


def osm() -> None:
    from shapely import STRtree
    from shapely.geometry import Point
    hr = _hranice()
    print(f"OSM: hranice {len(hr)} obcí")
    filtre = ('nwr(area.sk)[shop~"^(supermarket|convenience|greengrocer|butcher|bakery)$"];'
              'nwr(area.sk)[amenity~"^(restaurant|pub|cafe|fast_food|bar|charging_station)$"];'
              'nwr(area.sk)[leisure=playground];')
    body = _overpass(f"[out:json][timeout:900];{SK}({filtre});out tags center;")
    kody = list(hr)
    strom = STRtree([hr[k] for k in kody])
    obce = {k: [0] * len(OSM_KAT) for k in kody}
    nepr = 0
    for e in body:
        c = e.get("center") or ({"lat": e["lat"], "lon": e["lon"]} if "lat" in e else None)
        if not c:
            continue
        bod = Point(c["lon"], c["lat"])
        idx = [i for i in strom.query(bod) if hr[kody[i]].covers(bod)]
        if not idx:
            nepr += 1
            continue
        t = e.get("tags", {})
        for j, (_, f) in enumerate(OSM_KAT):
            if f(t):
                obce[kody[idx[0]]][j] += 1
    print(f"OSM: {len(body)} prvkov, mimo obcí {nepr}; {len(obce)} obcí; spolu "
          f"{dict(zip([k for k, _ in OSM_KAT], [sum(v[i] for v in obce.values()) for i in range(len(OSM_KAT))]))}")
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
