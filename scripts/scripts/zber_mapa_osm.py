"""Mapa krajských miest z OpenStreetMap (Overpass API) – pre mestá bez vlastného portálu a ako doplnok portálu.

Konfigurácia: src/mesta.json (osm_rel = relácia hraníc mesta v OSM).
Výstup: public/data/mesta/mapa-osm-<slug>.json – vrstvy v rovnakom formáte ako zber_mapa_mesta.py + hranice mesta.
Ak má mesto vlastnú mapu z portálu (mapa-<slug>.json), z OSM sa berú len vrstvy, ktoré portál nemá.

Licencia údajov: © prispievatelia OpenStreetMap, ODbL. Lekárov (ambulancie s menami) nezaraďujeme.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

from spolocne import KOREN, VEREJNE, s, spusti, zapis_ak_zmena

SERVERY = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))

# id vrstvy: (názov, skupina, Overpass filter, predvolený názov bodu, je aj v portáli mesta)
VRSTVY = {
    "lekarne": ("Lekárne", "Zdravie", 'nwr(area.a)["amenity"="pharmacy"];', "Lekáreň", False),
    "nemocnice": ("Nemocnice a polikliniky", "Zdravie", 'nwr(area.a)["amenity"~"^(hospital|clinic)$"];', "Zdravotnícke zariadenie", False),
    "skolky": ("Materské školy", "Školy", 'nwr(area.a)["amenity"="kindergarten"];', "Materská škola", True),
    "skoly": ("Základné a stredné školy", "Školy", 'nwr(area.a)["amenity"="school"];', "Škola", True),
    "vysoke": ("Vysoké školy", "Školy", 'nwr(area.a)["amenity"~"^(university|college)$"];', "Vysoká škola", False),
    "zastavky": ("Zastávky MHD", "Doprava", 'node(area.a)["highway"="bus_stop"];node(area.a)["railway"="tram_stop"];', "Zastávka", True),
    "nabijanie": ("Nabíjacie stanice", "Doprava", 'nwr(area.a)["amenity"="charging_station"];', "Nabíjacia stanica", False),
    "muzea": ("Múzeá a galérie", "Kultúra a turizmus", 'nwr(area.a)["tourism"~"^(museum|gallery)$"];', "Múzeum", True),
    "kultura": ("Divadlá, kiná a knižnice", "Kultúra a turizmus", 'nwr(area.a)["amenity"~"^(theatre|cinema|library|arts_centre)$"];', "Kultúrne zariadenie", True),
    "pamiatky": ("Hrady, kostoly a pamätníky", "Kultúra a turizmus", 'nwr(area.a)["historic"~"^(castle|monument|church|memorial)$"]["name"];', "Pamiatka", False),
    "ihriska": ("Detské ihriská", "Šport a voľný čas", 'nwr(area.a)["leisure"="playground"];', "Detské ihrisko", True),
    "sport": ("Športoviská a kúpaliská", "Šport a voľný čas", 'nwr(area.a)["leisure"~"^(sports_centre|swimming_pool|stadium)$"]["name"];', "Športovisko", False),
    "fontany": ("Pitná voda", "Šport a voľný čas", 'node(area.a)["amenity"="drinking_water"];', "Pitná voda", True),
    "parky": ("Parky", "Šport a voľný čas", 'nwr(area.a)["leisure"="park"]["name"];', "Park", False),
    "posty": ("Pošty", "Služby mesta", 'nwr(area.a)["amenity"="post_office"];', "Pošta", True),
    "urady": ("Úrady", "Služby mesta", 'nwr(area.a)["amenity"~"^(townhall|courthouse)$"];', "Úrad", False),
    "policia": ("Polícia", "Služby mesta", 'nwr(area.a)["amenity"="police"];', "Polícia", True),
}


# GDPR: názvy s akademickými titulmi sú spravidla ambulancie konkrétnych lekárov (fyzické osoby) – vynecháme ich
OSOBA = re.compile(r"\b(MUDr|MDDr|PharmDr|PhDr|RNDr|Mgr|Bc|Ing|JUDr|PaedDr|doc|prof)\b\.?", re.I)


def overpass(q: str) -> dict:
    posledna = None
    for kolo in range(3):
        if kolo:
            time.sleep(60 * kolo)  # verejné servery pri preťažení vracajú 429/504
        for u in SERVERY:
            try:
                r = s.post(u, data={"data": q}, timeout=300)
                if r.status_code == 200 and r.text.lstrip().startswith("{"):
                    return r.json()
                posledna = f"{u}: HTTP {r.status_code}"
            except Exception as e:  # noqa: BLE001
                posledna = f"{u}: {e}"
            time.sleep(5)
    raise RuntimeError(f"Overpass nedostupný ({posledna})")


def detail(t: dict, vid: str) -> dict:
    d = {}
    ul = " ".join(x for x in [t.get("addr:street") or t.get("addr:place"), t.get("addr:housenumber") or t.get("addr:conscriptionnumber")] if x)
    if ul:
        d["Adresa"] = ul
    if vid == "zastavky":
        linky = t.get("route_ref")
        if linky:
            d["Linky"] = linky.replace(";", ", ")
    for k, n in (("opening_hours", "Otváracie hodiny"), ("operator", "Prevádzkovateľ"), ("website", "Web"), ("contact:website", "Web"),
                 ("wheelchair", "Bezbariérový prístup"), ("socket:type2", "Zásuvky Type 2"), ("capacity", "Kapacita")):
        v = t.get(k)
        if v and n not in d and not (k == "operator" and OSOBA.search(v)):
            d[n] = {"yes": "áno", "no": "nie", "limited": "čiastočne"}.get(v, v)[:200]
    return d


def main() -> int:
    chyby = 0
    for m in MESTA:
        if not m.get("osm_rel") or m.get("plne"):
            continue
        ma_portal = (VEREJNE / "mesta" / f"mapa-{m['slug']}.json").exists()
        vybrane = {k: v for k, v in VRSTVY.items() if not (ma_portal and v[4])}
        area = 3600000000 + m["osm_rel"]
        casti = "".join(f"{v[2].replace(';', f';')}" for v in vybrane.values())
        try:
            # jeden dotaz na mesto; každý prvok zaradíme podľa značiek
            j = overpass(f"[out:json][timeout:240];area({area})->.a;({casti});out center tags;")
            hr = overpass(f"[out:json][timeout:120];relation({m['osm_rel']});out geom;")
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Mapa OSM {m['nazov']}::{e}")
            chyby += 1
            continue
        vrstvy: dict[str, list] = {k: [] for k in vybrane}
        videne = set()
        for e in j.get("elements", []):
            t = e.get("tags", {})
            lat = e.get("lat") or (e.get("center") or {}).get("lat")
            lon = e.get("lon") or (e.get("center") or {}).get("lon")
            if lat is None:
                continue
            a, le, hi = t.get("amenity", ""), t.get("leisure", ""), t.get("historic", "")
            vid = ("lekarne" if a == "pharmacy" else "nemocnice" if a in ("hospital", "clinic") else "skolky" if a == "kindergarten" else
                   "skoly" if a == "school" else "vysoke" if a in ("university", "college") else
                   "zastavky" if t.get("highway") == "bus_stop" or t.get("railway") == "tram_stop" else "nabijanie" if a == "charging_station" else
                   "muzea" if t.get("tourism") in ("museum", "gallery") else "kultura" if a in ("theatre", "cinema", "library", "arts_centre") else
                   "pamiatky" if hi in ("castle", "monument", "church", "memorial") else "ihriska" if le == "playground" else
                   "sport" if le in ("sports_centre", "swimming_pool", "stadium") else "fontany" if a == "drinking_water" else
                   "parky" if le == "park" else "posty" if a == "post_office" else "urady" if a in ("townhall", "courthouse") else
                   "policia" if a == "police" else None)
            if vid not in vrstvy or (vid, e["type"], e["id"]) in videne or OSOBA.search(t.get("name", "")):
                continue
            videne.add((vid, e["type"], e["id"]))
            vrstvy[vid].append([round(lat, 6), round(lon, 6), (t.get("name") or vybrane[vid][3]).strip(), detail(t, vid)])
        # zastávka má v OSM bod pre každý smer – zlúčime rovnomenné body do 250 m
        if vrstvy.get("zastavky"):
            zlucene: list = []
            for b in sorted(vrstvy["zastavky"], key=lambda x: (x[2], x[0], x[1])):
                z = next((x for x in zlucene if x[2] == b[2] and abs(x[0] - b[0]) < 0.0023 and abs(x[1] - b[1]) < 0.0034), None)
                if not z:
                    zlucene.append(b)
                elif b[3].get("Linky"):
                    linky = sorted({*z[3].get("Linky", "").split(", "), *b[3]["Linky"].split(", ")} - {""}, key=lambda x: (len(x), x))
                    z[3]["Linky"] = ", ".join(linky)
            vrstvy["zastavky"] = zlucene
        # hranice mesta (vonkajšie obrysy relácie)
        hranice = None
        rel = next((x for x in hr.get("elements", []) if x.get("type") == "relation"), None)
        if rel:
            ciary = [[[p["lon"], p["lat"]] for p in mb.get("geometry", [])] for mb in rel.get("members", []) if mb.get("role") == "outer" and mb.get("geometry")]
            hranice = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"n": m["nazov"]},
                                                                  "geometry": {"type": "MultiLineString", "coordinates": ciary}}]}
        vystup = [{"id": f"osm-{k}", "nazov": vybrane[k][0], "skupina": vybrane[k][1], "typ": "body", "body": sorted(b, key=lambda x: x[2]),
                   "zdroj": "https://www.openstreetmap.org/copyright"} for k, b in vrstvy.items() if b]
        if not vystup:
            chyby += 1
            continue
        zapis_ak_zmena(VEREJNE / "mesta" / f"mapa-osm-{m['slug']}.json", {"aktualizovane": datetime.now().isoformat(timespec="seconds"),
                       "zdroj": "OpenStreetMap", "licencia": "© prispievatelia OpenStreetMap (ODbL)", "hranice": hranice, "vrstvy": vystup}, kompaktne=True)
        print(f"{m['nazov']}: " + ", ".join(f"{v['nazov']} {len(v['body'])}" for v in vystup))
        time.sleep(20)
    if chyby >= 4:
        raise RuntimeError(f"Mapa OSM: {chyby} miest bez údajov")
    return 0


if __name__ == "__main__":
    spusti(main, "Mapa miest z OSM")
