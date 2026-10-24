"""Cyklistická infraštruktúra v Bratislave z OpenStreetMap (Overpass API).

Výstupy:
  data/cyklo-bratislava.json                 – kilometre podľa druhu a mestských častí
  public/data/cyklotrasy-bratislava.geojson  – zjednodušené čiary pre mapu (načíta sa až v prehliadači)

Kategórie (podľa značenia v OSM):
  cyklocesticka – samostatná cestička pre cyklistov (highway=cycleway)
  spolocna      – chodník/cestička pre chodcov a cyklistov (footway/path/pedestrian + bicycle=designated)
  cyklopruh     – vyznačený pruh alebo pás na ceste (cycleway*=lane|track pri ceste)

Dĺžky sa rátajú v metroch v projekcii UTM 33N, orezané hranicami mestských častí.
Údaje z OSM nie sú oficiálna evidencia mesta – závisia od toho, čo prispievatelia zmapovali.
Dáta © prispievatelia OpenStreetMap, licencia ODbL.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import LineString, shape
from shapely.ops import transform

KOREN = Path(__file__).resolve().parent.parent
DATA = KOREN / "data"
VYSTUP_STAT = DATA / "cyklo-bratislava.json"
VYSTUP_GEO = KOREN / "public" / "data" / "cyklotrasy-bratislava.geojson"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
SERVERY = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
DOTAZ = """
[out:json][timeout:240];
area["name"="Bratislava"]["boundary"="administrative"]->.ba;
(
  way(area.ba)["highway"="cycleway"];
  way(area.ba)["highway"~"^(footway|path|pedestrian|track|service)$"]["bicycle"="designated"];
  way(area.ba)["highway"]["cycleway"~"^(lane|track|opposite_lane|opposite_track)$"];
  way(area.ba)["highway"]["cycleway:right"~"^(lane|track)$"];
  way(area.ba)["highway"]["cycleway:left"~"^(lane|track)$"];
  way(area.ba)["highway"]["cycleway:both"~"^(lane|track)$"];
);
out tags geom;
"""
NAZVY = {
    "cyklocesticka": "Cyklocestičky",
    "spolocna": "Spoločné chodníky pre chodcov a cyklistov",
    "cyklopruh": "Cyklopruhy a pásy na ceste",
}


def stiahni() -> dict:
    chyby = []
    for server in SERVERY:
        for _ in range(2):
            try:
                r = requests.post(server, data={"data": DOTAZ}, headers={"User-Agent": UA}, timeout=280)
                r.raise_for_status()
                d = r.json()
                if d.get("elements"):
                    print(f"Overpass: {server}, {len(d['elements'])} ciest")
                    return d
                chyby.append(f"{server}: prázdne")
            except Exception as e:  # noqa: BLE001
                chyby.append(f"{server}: {type(e).__name__}")
            time.sleep(45)
    raise RuntimeError("Overpass neodpovedal: " + "; ".join(chyby))


def kategoria(t: dict) -> str | None:
    hw = t.get("highway")
    if hw == "cycleway":
        return "cyklocesticka"
    if t.get("bicycle") == "designated" and hw in ("footway", "path", "pedestrian", "track", "service"):
        # cestička s bicycle=designated, kde chodci nesmú, je de facto cyklocestička
        return "cyklocesticka" if hw == "path" and t.get("foot") == "no" else "spolocna"
    for k in ("cycleway", "cycleway:right", "cycleway:left", "cycleway:both"):
        if t.get(k, "").replace("opposite_", "") in ("lane", "track"):
            return "cyklopruh"
    return None


def main() -> int:
    data = stiahni()
    hranice = json.loads((DATA / "hranice-bratislava.geojson").read_text(encoding="utf-8"))
    obyv = json.loads((DATA / "obyvatelstvo-bratislava.json").read_text(encoding="utf-8"))
    rok = max(obyv["mesto"]["roky"])
    pocty = {c["kod"][-6:]: c["roky"][rok] for c in obyv["mestske_casti"]}
    nazvy = {c["kod"][-6:]: c["nazov_kratky"] for c in obyv["mestske_casti"]}

    do_utm = Transformer.from_crs(4326, 32633, always_xy=True).transform
    casti = []
    for f in hranice["features"]:
        g = shape(f["geometry"])
        casti.append((f["properties"]["kod_obce"], f["properties"]["rozloha_km2"], g, transform(do_utm, g)))

    km: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    prvky = []
    for e in data["elements"]:
        if e.get("type") != "way" or not e.get("geometry"):
            continue
        kat = kategoria(e.get("tags", {}))
        if not kat:
            continue
        ciara = LineString([(b["lon"], b["lat"]) for b in e["geometry"]])
        ciara_utm = transform(do_utm, ciara)
        v_meste = False
        for kod, _, _, g_utm in casti:
            if ciara_utm.intersects(g_utm):
                dlzka = ciara_utm.intersection(g_utm).length
                if dlzka > 0:
                    km[kod][kat] += dlzka / 1000
                    v_meste = True
        if v_meste:
            zj = ciara.simplify(0.00003)
            prvky.append({
                "type": "Feature",
                "properties": {"k": kat},
                "geometry": {"type": "LineString", "coordinates": [[round(x, 5), round(y, 5)] for x, y in zj.coords]},
            })
    if len(prvky) < 200:
        raise RuntimeError(f"Cyklo: podozrivo málo úsekov ({len(prvky)}).")

    po_castiach = []
    for kod, rozloha, _, _ in casti:
        k = km.get(kod, {})
        spolu = sum(k.values())
        po_castiach.append({
            "kod_obce": kod, "nazov": nazvy.get(kod, kod),
            "km": {kat: round(k.get(kat, 0), 1) for kat in NAZVY},
            "km_spolu": round(spolu, 1),
            "km_na_km2": round(spolu / rozloha, 2) if rozloha else None,
            "m_na_obyvatela": round(1000 * spolu / pocty[kod], 2) if pocty.get(kod) else None,
        })
    po_castiach.sort(key=lambda c: -c["km_spolu"])
    mesto = {kat: round(sum(c["km"][kat] for c in po_castiach), 1) for kat in NAZVY}

    VYSTUP_GEO.parent.mkdir(parents=True, exist_ok=True)
    VYSTUP_GEO.write_text(json.dumps({"type": "FeatureCollection", "features": prvky}, separators=(",", ":")) + "\n", encoding="utf-8")
    stat = {
        "zdroj": {"nazov": "OpenStreetMap", "licencia": "ODbL – © prispievatelia OpenStreetMap",
                  "url": "https://www.openstreetmap.org/copyright", "stav_osm": data.get("osm3s", {}).get("timestamp_osm_base")},
        "kategorie": NAZVY,
        "mesto": {"km": mesto, "km_spolu": round(sum(mesto.values()), 1)},
        "mestske_casti": po_castiach,
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    VYSTUP_STAT.write_text(json.dumps(stat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK cyklo: {stat['mesto']}, {len(prvky)} úsekov, geojson {VYSTUP_GEO.stat().st_size // 1024} kB")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber cyklotrás::{type(e).__name__}: {sprava}")
        sys.exit(1)
