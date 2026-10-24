"""Časti miest (mestské štvrte) z OpenStreetMap pre mestá, ktoré nemajú hranice mestských častí v otvorených dátach.

Bratislava a Košice majú mestské časti z oficiálnych zdrojov. Pre ostatné krajské mestá sa použijú relácie OSM:
  časti obce (boundary=administrative, admin_level 10/11) alebo katastrálne územia (boundary=cadastral).

Výstup: data/mesta/casti-osm.json – {slug: {zdroj, druh, casti: [{n, g (GeoJSON)}]}}
Licencia: © prispievatelia OpenStreetMap (ODbL).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from shapely.geometry import LineString, MultiPolygon, mapping
from shapely.ops import polygonize, unary_union

from spolocne import DATA, KOREN, spusti, zapis_ak_zmena
from zber_mapa_osm import overpass

MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))
# mesto → (dotaz na relácie v oblasti mesta, popis)
VYBER = {
    "zilina": ('rel(area.a)[boundary=administrative][admin_level=11];', "časti mesta"),
    "banska-bystrica": ('rel(area.a)[boundary=administrative][admin_level=11];', "časti mesta"),
    "trencin": ('rel(area.a)[boundary=administrative][admin_level=11];', "časti mesta"),
    # Prešov a Trnava nemajú v OSM hranice štvrtí – približné hranice z bodov štvrtí (place=suburb/quarter…), pozri VORONOI
    "nitra": ('rel(area.a)[boundary=cadastral];', "katastrálne územia"),
}


# mestá bez hraníc štvrtí: približné hranice – každé miesto mesta patrí k najbližšiemu bodu štvrte (Voronoiho oblasti)
VORONOI = {"presov", "trnava"}


def voronoi_casti(m: dict, hr) -> list[dict]:
    from shapely.geometry import MultiPoint, Point
    from shapely.ops import voronoi_diagram
    area = 3600000000 + m["osm_rel"]
    j = overpass(f'[out:json][timeout:120];area({area})->.a;(node(area.a)[place~"^(suburb|quarter|neighbourhood)$"][name];);out tags;')
    body = {}
    for e in j.get("elements", []):
        n = e["tags"]["name"].strip()
        if n and n != m["nazov"] and not n.startswith(m["nazov"] + " ") and n not in body and hr.contains(Point(e["lon"], e["lat"])):
            body[n] = (e["lon"], e["lat"])
    if len(body) < 5:
        return []
    bunky = voronoi_diagram(MultiPoint(list(body.values())), envelope=hr.envelope.buffer(0.05))
    out = []
    for n, (x, y) in body.items():
        b = next((c for c in bunky.geoms if c.contains(Point(x, y))), None)
        g = b.intersection(hr) if b is not None else None
        if g is not None and not g.is_empty and g.area > 0:
            out.append((n, g.simplify(0.00015, preserve_topology=True)))
    return out


def polygon(rel: dict):
    vonk = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in rel.get("members", []) if m.get("role") in ("outer", "") and len(m.get("geometry") or []) > 1]
    vnut = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in rel.get("members", []) if m.get("role") == "inner" and len(m.get("geometry") or []) > 1]
    if not vonk:
        return None
    g = unary_union(list(polygonize(unary_union(vonk))))
    if vnut:
        diery = unary_union(list(polygonize(unary_union(vnut))))
        g = g.difference(diery)
    if g.is_empty or g.area <= 0:
        return None
    return g.simplify(0.00015, preserve_topology=True)


def zaokruhli(gj: dict) -> dict:
    gj = json.loads(json.dumps(gj, default=list))
    def z(x):
        return [z(y) for y in x] if isinstance(x, (list, tuple)) and x and isinstance(x[0], (list, tuple)) else [round(x[0], 5), round(x[1], 5)]
    return {"type": gj["type"], "coordinates": z(gj["coordinates"])}


def main() -> int:
    out = {}
    for m in MESTA:
        if m["slug"] in VORONOI and m.get("osm_rel"):
            try:
                mesto = overpass(f"[out:json][timeout:120];relation({m['osm_rel']});out geom;")
                hr = next((polygon(x) for x in mesto.get("elements", []) if x.get("type") == "relation"), None)
                casti = [{"n": n, "g": zaokruhli(mapping(g))} for n, g in voronoi_casti(m, hr.buffer(0))] if hr is not None else []
            except Exception as e:  # noqa: BLE001
                print(f"::warning title=Časti {m['nazov']}::{e}")
                casti = []
            if len(casti) >= 4:
                out[m["slug"]] = {"zdroj": "https://www.openstreetmap.org/copyright", "licencia": "© prispievatelia OpenStreetMap (ODbL)",
                                  "druh": "štvrte", "priblizne": True, "casti": sorted(casti, key=lambda c: c["n"])}
            print(f"{m['nazov']}: {len(casti)} štvrtí (približné hranice z bodov OSM)")
            time.sleep(10)
            continue
        if m["slug"] not in VYBER or not m.get("osm_rel"):
            continue
        dotaz, druh = VYBER[m["slug"]]
        area = 3600000000 + m["osm_rel"]
        try:
            j = overpass(f"[out:json][timeout:240];area({area})->.a;({dotaz});out geom;")
            mesto = overpass(f"[out:json][timeout:120];relation({m['osm_rel']});out geom;")
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Časti {m['nazov']}::{e}")
            continue
        hr = next((polygon(x) for x in mesto.get("elements", []) if x.get("type") == "relation"), None)
        hr = hr.buffer(0) if hr is not None else None
        casti = []
        for r in j.get("elements", []):
            n = (r.get("tags") or {}).get("name", "").strip()
            g = polygon(r)
            if n == m["nazov"]:
                # časť s rovnakým názvom ako mesto: stred mesta (časti) alebo hlavné katastrálne územie
                n = "Centrum" if (r.get("tags") or {}).get("admin_level") == "11" else f"k. ú. {n}"
            if not n or g is None or n == m["nazov"] or n.startswith(m["nazov"] + " "):
                continue  # celé mesto alebo číslované obvody („Prešov 3“) nie sú štvrte
            if hr is not None and hr.area > 0 and not hr.buffer(0.003).contains(g.representative_point()):
                continue  # časť susednej obce
            if any(c["n"] == n for c in casti):
                continue
            gj = mapping(g if isinstance(g, MultiPolygon) or g.geom_type == "Polygon" else g.buffer(0))
            gj = json.loads(json.dumps(gj, default=list))
            def zaokr(x):
                return [zaokr(y) for y in x] if isinstance(x, (list, tuple)) and x and isinstance(x[0], (list, tuple)) else [round(x[0], 5), round(x[1], 5)]
            casti.append({"n": n, "g": {"type": gj["type"], "coordinates": zaokr(gj["coordinates"])}})
        casti.sort(key=lambda c: c["n"])
        if len(casti) >= 4:
            out[m["slug"]] = {"zdroj": "https://www.openstreetmap.org/copyright", "licencia": "© prispievatelia OpenStreetMap (ODbL)", "druh": druh, "casti": casti}
        print(f"{m['nazov']}: {len(casti)} častí ({druh})")
        time.sleep(10)
    if not out:
        raise RuntimeError("Časti miest z OSM: žiadne údaje")
    zapis_ak_zmena(DATA / "mesta" / "casti-osm.json", {"mesta": out, "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return 0


if __name__ == "__main__":
    spusti(main, "Časti miest (OSM)")
