"""Hranice mestských častí Bratislavy z OpenStreetMap (Overpass API).

Výstup: data/hranice-bratislava.geojson

Hranice sa menia zriedka, preto skript nebeží každú noc – spúšťa sa ručne
(GitHub → Actions → Hranice → Run workflow) alebo pri zmene tohto skriptu.

OSM: mestské časti sú relácie boundary=administrative, admin_level=9,
tag ref = kód obce (napr. 528595 = Staré Mesto). Rovnaký kód je na konci
kódu obce v DATAcube (SK0101528595), takže dáta sa dajú spárovať.

Dáta © prispievatelia OpenStreetMap, licencia ODbL.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from pyproj import Geod
from shapely.geometry import LineString, mapping
from shapely.ops import polygonize, unary_union

VYSTUP = Path(__file__).resolve().parent.parent / "data" / "hranice-bratislava.geojson"
SERVERY = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
DOTAZ = """
[out:json][timeout:180];
area["name"="Bratislava"]["boundary"="administrative"]->.ba;
rel(area.ba)["boundary"="administrative"]["admin_level"="9"]["ref"];
out geom;
"""
OCAKAVANY_POCET = 17
ZJEDNODUSENIE = 0.00005  # stupne (~4 m) – menší súbor, na mape nepostrehnuteľné
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"


def stiahni() -> dict:
    chyby = []
    for server in SERVERY:
        for pokus in range(2):
            try:
                r = requests.post(server, data={"data": DOTAZ}, headers={"User-Agent": UA}, timeout=240)
                r.raise_for_status()
                data = r.json()
                if data.get("elements"):
                    print(f"Overpass: {server}")
                    return data
                chyby.append(f"{server}: prázdna odpoveď")
            except Exception as e:  # noqa: BLE001
                chyby.append(f"{server}: {type(e).__name__}")
            time.sleep(10)
    raise RuntimeError("Žiadny Overpass server neodpovedal: " + "; ".join(chyby))


def polygon_relacie(rel: dict):
    vonkajsie, vnutorne = [], []
    for m in rel.get("members", []):
        if m.get("type") != "way" or not m.get("geometry"):
            continue
        ciara = LineString([(b["lon"], b["lat"]) for b in m["geometry"]])
        (vnutorne if m.get("role") == "inner" else vonkajsie).append(ciara)
    plocha = unary_union(list(polygonize(vonkajsie)))
    if vnutorne:
        plocha = plocha.difference(unary_union(list(polygonize(vnutorne))))
    if plocha.is_empty:
        raise RuntimeError(f"Relácia {rel['id']} ({rel['tags'].get('name')}): nepodarilo sa zložiť polygón.")
    return plocha


def zaokruhli(geo):
    if isinstance(geo, (list, tuple)):
        if geo and isinstance(geo[0], (int, float)):
            return [round(geo[0], 5), round(geo[1], 5)]
        return [zaokruhli(g) for g in geo]
    return geo


def main() -> int:
    data = stiahni()
    geod = Geod(ellps="WGS84")
    prvky = []
    for rel in data["elements"]:
        t = rel.get("tags", {})
        plocha = polygon_relacie(rel)
        rozloha_km2 = abs(geod.geometry_area_perimeter(plocha)[0]) / 1e6
        zjednodusena = plocha.simplify(ZJEDNODUSENIE, preserve_topology=True)
        geo = mapping(zjednodusena)
        nazov = t.get("name", "").replace("Bratislava-", "").replace("Bratislava - ", "").strip()
        prvky.append({
            "type": "Feature",
            "properties": {
                "kod_obce": t["ref"],
                "nazov": nazov,
                "rozloha_km2": round(rozloha_km2, 2),
                "osm_id": rel["id"],
            },
            "geometry": {"type": geo["type"], "coordinates": zaokruhli(geo["coordinates"])},
        })
    if len(prvky) != OCAKAVANY_POCET:
        nazvy = ", ".join(p["properties"]["nazov"] for p in prvky)
        raise RuntimeError(f"Čakal som {OCAKAVANY_POCET} mestských častí, prišlo {len(prvky)}: {nazvy}")
    prvky.sort(key=lambda p: p["properties"]["nazov"])
    vystup = {
        "type": "FeatureCollection",
        "zdroj": {
            "nazov": "OpenStreetMap",
            "licencia": "ODbL – © prispievatelia OpenStreetMap",
            "url": "https://www.openstreetmap.org/copyright",
            "stav_osm": data.get("osm3s", {}).get("timestamp_osm_base"),
        },
        "features": prvky,
    }
    VYSTUP.parent.mkdir(parents=True, exist_ok=True)
    VYSTUP.write_text(json.dumps(vystup, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    spolu = sum(p["properties"]["rozloha_km2"] for p in prvky)
    print(f"OK: {len(prvky)} mestských častí, spolu {spolu:.1f} km², {VYSTUP.stat().st_size // 1024} kB")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber hraníc::{type(e).__name__}: {sprava}")
        sys.exit(1)
