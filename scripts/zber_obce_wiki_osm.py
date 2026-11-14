"""Obce z Wikidata a OpenStreetMap.

  wiki – Wikidata: prvá písomná zmienka (P1249) a nadmorská výška (P2044); obec podľa LAU kódu (P782, posledných 6 číslic = kód obce).
  osm  – OpenStreetMap (Overpass): počet obchodov s potravinami, reštaurácií/kaviarní/pohostinstiev, detských ihrísk a nabíjacích
         staníc v hraniciach obce (admin_level 8 s tagom ref = kód obce; Bratislava a Košice cez svoje okresy).
         Úplnosť OSM sa medzi obcami líši – na webe s poznámkou.

  pamiatky – Wikidata: pamiatkové objekty a národné kultúrne pamiatky (P1435 = Q112086057 / Q960335), UNESCO (Q9259);
             obec cez P131 (miesto alebo jeho nadradená časť obce). Počet + najznámejšie podľa počtu jazykových verzií.
  trasy – OpenStreetMap: dĺžka cyklotrás (route=bicycle/mtb) a turistických trás (route=hiking) v katastri obce, km.

Výstupy data/obce/wiki.json, data/obce/osm.json, data/obce/pamiatky.json, data/obce/trasy.json.
Hranice obcí z OSM sa v rámci behu cachujú (/tmp) – používa ich aj zber_obce_vrstvy.py.
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
    ("zastavky", lambda t: t.get("highway") == "bus_stop"),  # počíta sa podľa názvu (dve nástupištia = 1 zastávka)
    ("bankomaty", lambda t: t.get("amenity") == "atm"),
    ("sport", lambda t: t.get("leisure") in ("pitch", "sports_centre", "stadium", "sports_hall")),
    ("kostoly", lambda t: t.get("amenity") == "place_of_worship"),
    ("cintoriny", lambda t: t.get("landuse") == "cemetery"),
    ("hasici", lambda t: t.get("amenity") == "fire_station"),
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


def hranice() -> dict[str, object]:
    """Hranice obcí s cache v /tmp (platná 12 h) – spoločné pre OSM, trasy a chránené územia."""
    import pickle
    import tempfile
    from pathlib import Path
    c = Path(tempfile.gettempdir()) / "obce_hranice.pkl"
    if c.exists() and time.time() - c.stat().st_mtime < 12 * 3600:
        return pickle.loads(c.read_bytes())
    hr = _hranice()
    if len(hr) > 2500:
        c.write_bytes(pickle.dumps(hr))
    return hr


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
    hr = hranice()
    print(f"OSM: hranice {len(hr)} obcí")
    filtre = ('nwr(area.sk)[shop~"^(supermarket|convenience|greengrocer|butcher|bakery)$"];'
              'nwr(area.sk)[amenity~"^(restaurant|pub|cafe|fast_food|bar|charging_station|atm|place_of_worship|fire_station)$"];'
              'nwr(area.sk)[leisure~"^(playground|pitch|sports_centre|stadium|sports_hall)$"];'
              'node(area.sk)[highway=bus_stop];way(area.sk)[landuse=cemetery];')
    body = _overpass(f"[out:json][timeout:900];{SK}({filtre});out tags center;")
    kody = list(hr)
    strom = STRtree([hr[k] for k in kody])
    obce = {k: [0] * len(OSM_KAT) for k in kody}
    zast: dict[str, set] = {k: set() for k in kody}
    iz = [k for k, _ in OSM_KAT].index("zastavky")
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
        kod = kody[idx[0]]
        for j, (_, f) in enumerate(OSM_KAT):
            if f(t):
                if j == iz:
                    zast[kod].add(t.get("name") or f"#{e.get('id')}")
                else:
                    obce[kod][j] += 1
    for kod, z in zast.items():
        obce[kod][iz] = len(z)
    print(f"OSM: {len(body)} prvkov, mimo obcí {nepr}; {len(obce)} obcí; spolu "
          f"{dict(zip([k for k, _ in OSM_KAT], [sum(v[i] for v in obce.values()) for i in range(len(OSM_KAT))]))}")
    if len(obce) < 2500:
        raise RuntimeError(f"OSM: len {len(obce)} obcí")
    zapis("osm", {"kategorie": [k for k, _ in OSM_KAT], "datum": datetime.now(timezone.utc).date().isoformat(),
                  "zdroj": {"nazov": "© prispievatelia OpenStreetMap (ODbL)", "url": "https://www.openstreetmap.org/copyright"},
                  "obce": dict(sorted(obce.items()))})


def pamiatky() -> None:
    q = """SELECT DISTINCT ?x ?lau ?d ?sl ?nazov WHERE {
      VALUES ?d { wd:Q112086057 wd:Q960335 wd:Q9259 }
      ?x wdt:P1435 ?d ; wdt:P131/wdt:P131? ?o . ?o wdt:P17 wd:Q214 ; wdt:P782 ?lau .
      OPTIONAL { ?x wikibase:sitelinks ?sl }
      OPTIONAL { ?x rdfs:label ?nazov FILTER(lang(?nazov) = "sk") } }"""
    r = s.post("https://query.wikidata.org/sparql", data={"query": q, "format": "json"}, headers=UA, timeout=600)
    r.raise_for_status()
    obj: dict[str, dict] = {}
    for b in r.json()["results"]["bindings"]:
        kod = b["lau"]["value"][-6:]
        if kod not in KODY:
            continue
        x = b["x"]["value"].rsplit("/", 1)[-1]
        o = obj.setdefault(x, {"kod": kod, "unesco": False, "pam": False, "sl": 0, "nazov": None})
        if o["kod"] != kod and o["kod"] not in KODY:
            o["kod"] = kod
        d = b["d"]["value"].rsplit("/", 1)[-1]
        if d == "Q9259":
            o["unesco"] = True
        else:
            o["pam"] = True
        o["sl"] = max(o["sl"], int(b.get("sl", {}).get("value", 0)))
        if "nazov" in b:
            o["nazov"] = b["nazov"]["value"]
    obce: dict[str, dict] = {}
    for x, o in obj.items():
        v = obce.setdefault(o["kod"], {"n": 0, "unesco": 0, "top": []})
        if o["pam"]:
            v["n"] += 1
            if o["nazov"] and o["sl"] >= 2:
                v["top"].append((o["sl"], o["nazov"]))
        if o["unesco"]:
            v["unesco"] = 1
    for v in obce.values():
        top = []
        for _, n in sorted(v["top"], key=lambda t: -t[0]):
            if n not in top:
                top.append(n)
        v["top"] = top[:4]
        if not v["unesco"]:
            del v["unesco"]
    print(f"Pamiatky: {len(obj)} objektov, {len(obce)} obcí, UNESCO {sum(1 for v in obce.values() if v.get('unesco'))}, spolu {sum(v['n'] for v in obce.values())}")
    if len(obce) < 1000:
        raise RuntimeError(f"Pamiatky: len {len(obce)} obcí")
    zapis("pamiatky", {"zdroj": {"nazov": "Wikidata – pamiatkové objekty a národné kultúrne pamiatky (podľa ÚZPF Pamiatkového úradu SR)", "url": "https://www.wikidata.org"},
                       "obce": dict(sorted(obce.items()))})


def trasy() -> None:
    import math
    import shapely
    from shapely import STRtree
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    hr = hranice()
    el = _overpass(f'[out:json][timeout:900];{SK}rel(area.sk)[type=route][route~"^(bicycle|mtb|hiking)$"];out geom;')
    ciary: dict[str, list] = {"cyklo": [], "turist": []}
    for e in el:
        typ = "turist" if e.get("tags", {}).get("route") == "hiking" else "cyklo"
        for m in e.get("members", []):
            if m.get("type") == "way" and m.get("geometry") and len(m["geometry"]) > 1:
                ciary[typ].append(LineString([(p["lon"], p["lat"]) for p in m["geometry"]]))
    kx, ky = 111.32 * math.cos(math.radians(48.7)), 110.574  # km na stupeň (SR leží medzi 47,7° a 49,6° s. š.)
    kody = list(hr)
    out = {k: [0.0, 0.0] for k in kody}
    for i, typ in enumerate(("cyklo", "turist")):
        if not ciary[typ]:
            continue
        siet = unary_union(ciary[typ])  # spoločné úseky viacerých trás len raz
        kusy = list(getattr(siet, "geoms", [siet]))
        strom = STRtree(kusy)
        for kod in kody:
            pol = hr[kod]
            idx = strom.query(pol)
            if len(idx) == 0:
                continue
            g = shapely.intersection(shapely.union_all([kusy[j] for j in idx]), pol)
            out[kod][i] = round(shapely.transform(g, lambda c: c * [kx, ky]).length, 1)
    out = {k: v for k, v in out.items() if v[0] or v[1]}
    print(f"Trasy: {len(el)} relácií, obcí {len(out)}, cyklo {round(sum(v[0] for v in out.values()))} km, turistické {round(sum(v[1] for v in out.values()))} km")
    if len(out) < 1500:
        raise RuntimeError(f"Trasy: len {len(out)} obcí")
    zapis("trasy", {"polia": ["cyklotrasy km", "turistické trasy km"], "datum": datetime.now(timezone.utc).date().isoformat(),
                    "zdroj": {"nazov": "© prispievatelia OpenStreetMap (ODbL) – cyklotrasy a turistické trasy", "url": "https://www.openstreetmap.org/copyright"},
                    "obce": dict(sorted(out.items()))})


def obrazky() -> None:
    """Erb (P94) a fotka obce (P18) z Wikimedia Commons s autorom a licenciou, partnerské mestá (P190) z Wikidata."""
    q = """SELECT ?lau ?erb ?foto ?pl WHERE { ?o wdt:P17 wd:Q214 ; wdt:P782 ?lau .
      OPTIONAL { ?o wdt:P94 ?erb } OPTIONAL { ?o wdt:P18 ?foto }
      OPTIONAL { ?o wdt:P190 ?p . ?p rdfs:label ?pl FILTER(lang(?pl) = "sk") } }"""
    r = s.post("https://query.wikidata.org/sparql", data={"query": q, "format": "json"}, headers=UA, timeout=600)
    r.raise_for_status()
    obce: dict[str, dict] = {}
    nazov = lambda u: requests_unquote(u.rsplit("/", 1)[-1])  # noqa: E731
    for b in r.json()["results"]["bindings"]:
        kod = b["lau"]["value"][-6:]
        if kod not in KODY:
            continue
        o = obce.setdefault(kod, {})
        if "erb" in b and "erb" not in o:
            o["erb"] = nazov(b["erb"]["value"])
        if "foto" in b and "foto" not in o:
            o["foto"] = nazov(b["foto"]["value"])
        if "pl" in b:
            pl = o.setdefault("partneri", [])
            if b["pl"]["value"] not in pl:
                pl.append(b["pl"]["value"])
    # autor a licencia z Commons (po 50 súboroch)
    subory = sorted({o[k] for o in obce.values() for k in ("erb", "foto") if k in o})
    meta: dict[str, dict] = {}
    for i in range(0, len(subory), 50):
        dav = subory[i:i + 50]
        for pokus in range(3):
            try:
                rr = s.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=120, params={
                    "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "extmetadata|url", "iiurlwidth": 480,
                    "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl", "titles": "|".join("File:" + x for x in dav)})
                rr.raise_for_status()
                break
            except Exception:  # noqa: BLE001
                time.sleep(10)
        else:
            continue
        j = rr.json().get("query", {})
        norm = {n["to"]: n["from"] for n in j.get("normalized", [])}
        for pg in j.get("pages", {}).values():
            ii = (pg.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata") or {}
            autor = re.sub(r"<[^>]+>", "", (em.get("Artist") or {}).get("value", "")).strip()
            autor = re.sub(r"\s+", " ", autor)[:80]
            meno = norm.get(pg.get("title", ""), pg.get("title", "")).removeprefix("File:")
            if ii.get("thumburl"):
                meta[meno] = {"u": ii["thumburl"], "a": autor, "l": (em.get("LicenseShortName") or {}).get("value", ""), "lu": (em.get("LicenseUrl") or {}).get("value", "")}
        time.sleep(1)
    out = {}
    for kod, o in obce.items():
        v = {}
        for k in ("erb", "foto"):
            m = meta.get(o.get(k, "").replace("_", " ")) or meta.get(o.get(k, ""))
            if m:
                v[k] = {**m, "s": o[k]}
        if o.get("partneri"):
            v["partneri"] = sorted(o["partneri"])[:12]
        if v:
            out[kod] = v
    print(f"Obrázky: {len(out)} obcí, erb {sum('erb' in v for v in out.values())}, foto {sum('foto' in v for v in out.values())}, partneri {sum('partneri' in v for v in out.values())}")
    if sum("erb" in v for v in out.values()) < 1000:
        raise RuntimeError("Commons: málo erbov")
    zapis("obrazky", {"zdroj": {"nazov": "Wikidata a Wikimedia Commons – erb, fotografia, partnerské mestá", "url": "https://commons.wikimedia.org"},
                      "obce": dict(sorted(out.items()))})


def requests_unquote(x: str) -> str:
    from urllib.parse import unquote
    return unquote(x)


MODULY = {"wiki": wiki, "obrazky": obrazky, "pamiatky": pamiatky, "osm": osm, "trasy": trasy}


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
