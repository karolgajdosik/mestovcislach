"""Vybavenosť Bratislavy z OpenStreetMap: lekárne, zdravotníctvo, nabíjacie stanice, kultúra.

Pri bodoch pre mapu ukladáme aj podrobnosti z OSM: adresu, otváracie hodiny, web,
odkaz na Wikipédiu a fotku (Wikimedia Commons – priamo z OSM alebo cez Wikidata P18).
Telefóny ani e-maily nezverejňujeme.

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
  nwr(area.ba)["tourism"~"^(museum|gallery)$"];
  nwr(area.ba)["amenity"~"^(theatre|cinema|library|arts_centre)$"];
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


KULTURA = {"muzea": "Múzeá a galérie", "kultura": "Divadlá, kiná a knižnice"}


def kategoria(t: dict) -> str | None:
    a, h = t.get("amenity"), t.get("healthcare")
    if t.get("natural") == "tree":
        return "stromy"
    if t.get("tourism") in ("museum", "gallery"):
        return "muzea"
    if a in ("theatre", "cinema", "library", "arts_centre"):
        return "kultura"
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


def web(url: str | None) -> str | None:
    if not url:
        return None
    url = url.split(";")[0].strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url if "." in url and " " not in url else None


def commons(subor: str | None) -> str | None:
    """Odkaz na zmenšený obrázok z Wikimedia Commons (šírka 400 px)."""
    if not subor:
        return None
    subor = subor.strip()
    if subor.startswith("Category:"):
        return None
    subor = subor.removeprefix("File:").removeprefix("Súbor:")
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + requests.utils.quote(subor.replace(" ", "_")) + "?width=400"


def detaily(e: dict, t: dict) -> dict:
    d: dict = {"id": e["type"][0] + str(e["id"])}
    ulica = t.get("addr:street") or t.get("addr:place")
    if ulica:
        d["a"] = f"{ulica} {t.get('addr:housenumber') or t.get('addr:conscriptionnumber') or ''}".strip()
    if t.get("opening_hours"):
        d["h"] = t["opening_hours"][:200]
    w = web(t.get("website") or t.get("contact:website") or t.get("url"))
    if w:
        d["w"] = w
    if t.get("wikipedia") and ":" in t["wikipedia"]:
        jazyk, nazov = t["wikipedia"].split(":", 1)
        d["wp"] = f"https://{jazyk}.wikipedia.org/wiki/" + requests.utils.quote(nazov.replace(" ", "_"))
    img = t.get("image", "")
    if t.get("wikimedia_commons", "").startswith("File:"):
        d["f"] = commons(t["wikimedia_commons"])
    elif "commons.wikimedia.org" in img and "File:" in img:
        d["f"] = commons(img.split("File:", 1)[1])
    if t.get("wikidata"):
        d["wd"] = t["wikidata"]
    for k, kl in (("operator", "op"), ("capacity", "kap"), ("description", "pop")):
        if t.get(k):
            d[kl] = t[k][:120]
    return d


def fotky_z_wikidata(ids: list[str]) -> dict[str, dict]:
    """Wikidata: obrázok (P18) a slovenská Wikipédia pre zoznam Q-identifikátorov."""
    vysledok: dict[str, dict] = {}
    for i in range(0, len(ids), 50):
        davka = ids[i:i + 50]
        try:
            r = requests.get("https://www.wikidata.org/w/api.php", params={
                "action": "wbgetentities", "ids": "|".join(davka), "props": "claims|sitelinks", "sitefilter": "skwiki", "format": "json",
            }, headers={"User-Agent": UA}, timeout=60).json()
        except Exception as e:  # noqa: BLE001
            print(f"Wikidata: {e}")
            continue
        for q, ent in r.get("entities", {}).items():
            out = {}
            p18 = ent.get("claims", {}).get("P18")
            if p18:
                out["f"] = commons(p18[0]["mainsnak"].get("datavalue", {}).get("value"))
            sk = ent.get("sitelinks", {}).get("skwiki")
            if sk:
                out["wp"] = "https://sk.wikipedia.org/wiki/" + requests.utils.quote(sk["title"].replace(" ", "_"))
            if out:
                vysledok[q] = out
        time.sleep(1)
    return vysledok


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
        det = detaily(e, t)
        if kat in ("pamiatky", "stromy", "muzea", "kultura"):
            nazov = (t.get("name:sk") or t.get("name") or t.get("species:sk") or t.get("species") or "").strip()[:70]
            if kat == "kultura":
                det["typ"] = {"theatre": "Divadlo", "cinema": "Kino", "library": "Knižnica", "arts_centre": "Kultúrne centrum"}.get(t.get("amenity"), "")
            elif kat == "muzea":
                det["typ"] = "Galéria" if t.get("tourism") == "gallery" else "Múzeum"
            pamiatky_body.append([round(lat, 5), round(lon, 5), kat, nazov, det])
            continue
        if kat == "nabijanie":
            try:
                nabijacie_body[kod] += int(t.get("capacity", "1"))
            except ValueError:
                nabijacie_body[kod] += 1
        body.append([round(lat, 5), round(lon, 5), kat, (t.get("name") or t.get("operator") or "").strip()[:60], det])
    if len(body) < 200:
        raise RuntimeError(f"Vybavenosť: podozrivo málo prvkov ({len(body)}).")

    # Fotky a Wikipédia z Wikidata (len kultúra, pamiatky a nemocnice – tam má fotka zmysel)
    vsetky = body + pamiatky_body
    ids = sorted({b[4]["wd"] for b in vsetky if b[4].get("wd") and b[2] in ("pamiatky", "muzea", "kultura", "nemocnice", "stromy")})
    wd = fotky_z_wikidata(ids)
    for b in vsetky:
        q = b[4].pop("wd", None)
        if q in wd:
            for k, v in wd[q].items():
                b[4].setdefault(k, v)
    print(f"Wikidata: {len(ids)} položiek, fotka/Wikipédia pre {len(wd)}; "
          f"fotky spolu {sum(1 for b in vsetky if b[4].get('f'))}, hodiny {sum(1 for b in vsetky if b[4].get('h'))}, web {sum(1 for b in vsetky if b[4].get('w'))}")

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
    for k in KULTURA:
        mesto[k] = sum(pocty[kod].get(k, 0) for kod, _ in casti)

    zdroj = {"nazov": "OpenStreetMap", "licencia": "ODbL – © prispievatelia OpenStreetMap",
             "url": "https://www.openstreetmap.org/copyright", "stav_osm": data.get("osm3s", {}).get("timestamp_osm_base")}
    (KOREN / "public" / "data").mkdir(parents=True, exist_ok=True)
    (KOREN / "public" / "data" / "vybavenost-bratislava.json").write_text(
        json.dumps({"kategorie": KATEGORIE, "body": body}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (KOREN / "public" / "data" / "pamiatky-bratislava.json").write_text(
        json.dumps({"kategorie": {"pamiatky": "Kultúrne pamiatky", "stromy": "Chránené stromy", **KULTURA}, "body": pamiatky_body},
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
