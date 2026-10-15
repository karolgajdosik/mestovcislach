"""Vybavenosť Bratislavy z OpenStreetMap: lekárne, zdravotníctvo, nabíjacie stanice.

Výstupy:
  data/vybavenost-bratislava.json            – počty podľa mestských častí
  public/data/vybavenost-bratislava.json     – body pre mapu (načíta sa v prehliadači)

Tieto témy portál data.bratislava.sk nemá (na rozdiel napr. od Trnavského kraja),
preto ich berieme z OSM. Nejde o oficiálne registre – úplnosť závisí od zmapovania.
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
from shapely.geometry import Point, shape
from shapely.prepared import prep

KOREN = Path(__file__).resolve().parent.parent
DATA = KOREN / "data"
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
  nwr(area.ba)["amenity"="pharmacy"];
  nwr(area.ba)["amenity"~"^(doctors|clinic|hospital|dentist)$"];
  nwr(area.ba)["healthcare"~"^(doctor|clinic|hospital|dentist)$"];
  nwr(area.ba)["amenity"="charging_station"];
  nwr(area.ba)["heritage"];
  node(area.ba)["natural"="tree"]["denotation"="natural_monument"];
  node(area.ba)["natural"="tree"]["protected"="yes"];
  node(area.ba)["natural"="tree"]["protection_title"];
);
out center tags;
"""
KATEGORIE = {
    "lekarne": "Lekárne",
    "ambulancie": "Ambulancie a zubári",
    "nemocnice": "Nemocnice a polikliniky",
    "nabijanie": "Nabíjacie stanice",
}


def kategoria(t: dict) -> str | None:
    a, h = t.get("amenity"), t.get("healthcare")
    if t.get("natural") == "tree":
        return "stromy"
    if t.get("heritage") and not a and not h:
        return "pamiatky"
    if a == "pharmacy" or h == "pharmacy":
        return "lekarne"
    if a == "charging_station":
        return "nabijanie"
    if a == "hospital" or h == "hospital" or a == "clinic" or h == "clinic":
        return "nemocnice"
    if a in ("doctors", "dentist") or h in ("doctor", "dentist"):
        return "ambulancie"
    return None


def stiahni() -> dict:
    chyby = []
    for server in SERVERY:
        for _ in range(2):
            try:
                r = requests.post(server, data={"data": DOTAZ}, headers={"User-Agent": UA}, timeout=280)
                r.raise_for_status()
                d = r.json()
                if d.get("elements"):
                    print(f"Overpass: {server}, {len(d['elements'])} prvkov")
                    return d
                chyby.append(f"{server}: prázdne")
            except Exception as e:  # noqa: BLE001
                chyby.append(f"{server}: {type(e).__name__}")
            time.sleep(45)
    raise RuntimeError("Overpass neodpovedal: " + "; ".join(chyby))


def main() -> int:
    time.sleep(20)  # odstup od predchádzajúceho dotazu (cyklotrasy) – Overpass obmedzuje frekvenciu
    data = stiahni()
    hranice = json.loads((DATA / "hranice-bratislava.geojson").read_text(encoding="utf-8"))
    obyv = json.loads((DATA / "obyvatelstvo-bratislava.json").read_text(encoding="utf-8"))
    rok = max(obyv["mesto"]["roky"])
    pocty_obyv = {c["kod"][-6:]: c["roky"][rok] for c in obyv["mestske_casti"]}
    nazvy = {c["kod"][-6:]: c["nazov_kratky"] for c in obyv["mestske_casti"]}
    casti = [(f["properties"]["kod_obce"], prep(shape(f["geometry"]))) for f in hranice["features"]]

    pocty: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pamiatky_body = []
    nabijacie_body: dict[str, int] = defaultdict(int)
    body = []
    videne = set()
    for e in data["elements"]:
        kluc = (e["type"], e["id"])
        if kluc in videne:
            continue
        videne.add(kluc)
        t = e.get("tags", {})
        kat = kategoria(t)
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if not kat or lat is None:
            continue
        p = Point(lon, lat)
        kod = next((k for k, g in casti if g.contains(p)), None)
        if not kod:
            continue
        pocty[kod][kat] += 1
        if kat in ("pamiatky", "stromy"):
            pamiatky_body.append([round(lat, 5), round(lon, 5), kat, (t.get("name") or t.get("species:sk") or t.get("species") or "").strip()[:70]])
            continue
        if kat == "nabijanie":
            try:
                nabijacie_body[kod] += int(t.get("capacity", "1"))
            except ValueError:
                nabijacie_body[kod] += 1
        body.append([round(lat, 5), round(lon, 5), kat, (t.get("name") or t.get("operator") or "").strip()[:60]])
    if len(body) < 200:
        raise RuntimeError(f"Vybavenosť: podozrivo málo prvkov ({len(body)}).")

    po_castiach = []
    for kod, _ in casti:
        o = pocty_obyv.get(kod)
        po_castiach.append({
            "kod_obce": kod, "nazov": nazvy.get(kod, kod), "obyvatelia": o,
            **{k: pocty[kod].get(k, 0) for k in KATEGORIE},
            "nabijacie_miesta": nabijacie_body.get(kod, 0),
            "pamiatky": pocty[kod].get("pamiatky", 0), "stromy": pocty[kod].get("stromy", 0),
            "lekarne_na_10000": round(10000 * pocty[kod].get("lekarne", 0) / o, 1) if o else None,
            "ambulancie_na_10000": round(10000 * pocty[kod].get("ambulancie", 0) / o, 1) if o else None,
        })
    po_castiach.sort(key=lambda c: c["nazov"])
    mesto = {k: sum(c[k] for c in po_castiach) for k in KATEGORIE}
    mesto["nabijacie_miesta"] = sum(c["nabijacie_miesta"] for c in po_castiach)
    mesto["pamiatky"] = sum(c["pamiatky"] for c in po_castiach)
    mesto["stromy"] = sum(c["stromy"] for c in po_castiach)

    zdroj = {"nazov": "OpenStreetMap", "licencia": "ODbL – © prispievatelia OpenStreetMap",
             "url": "https://www.openstreetmap.org/copyright", "stav_osm": data.get("osm3s", {}).get("timestamp_osm_base")}
    (KOREN / "public" / "data").mkdir(parents=True, exist_ok=True)
    (KOREN / "public" / "data" / "vybavenost-bratislava.json").write_text(
        json.dumps({"kategorie": KATEGORIE, "body": body}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (KOREN / "public" / "data" / "pamiatky-bratislava.json").write_text(
        json.dumps({"kategorie": {"pamiatky": "Kultúrne pamiatky", "stromy": "Chránené stromy"}, "body": pamiatky_body},
                   ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (DATA / "vybavenost-bratislava.json").write_text(json.dumps({
        "zdroj": zdroj, "kategorie": KATEGORIE, "mesto": mesto, "mestske_casti": po_castiach,
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK vybavenosť: {mesto}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber vybavenosti::{type(e).__name__}: {sprava}")
        sys.exit(1)
