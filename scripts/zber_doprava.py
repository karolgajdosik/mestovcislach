"""MHD v Bratislave z cestovných poriadkov GTFS (Dopravný podnik Bratislava).

Výstup: data/doprava-bratislava.json

Zdroj: data.bratislava.sk – „Cestovné poriadky MHD vo formáte GTFS“ (CC BY 4.0),
súbor ZIP stiahnutý cez ArcGIS (…/content/items/<id>/data).

Počítame pre jeden typický pracovný deň (najbližšia streda v období platnosti
cestovného poriadku, ktorá nie je výnimkou):
  - zastávky (platformy rovnakého názvu zlúčené do jednej zastávky),
  - odchody = zastavenia spojov (bez poslednej zastávky spoja),
  - linky podľa druhu dopravy,
  - všetko aj po mestských častiach (podľa hraníc z data/hranice-bratislava.geojson).
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from shapely.geometry import Point, shape
from shapely.prepared import prep

DATA = Path(__file__).resolve().parent.parent / "data"
VYSTUP = DATA / "doprava-bratislava.json"
GTFS_ID = "aba12fd2cbac4843bc7406151bc66106"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
DRUHY = {"0": "Električky", "11": "Trolejbusy", "3": "Autobusy", "800": "Trolejbusy", "900": "Električky", "700": "Autobusy"}


def stiahni_gtfs() -> tuple[zipfile.ZipFile, dict]:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    meta = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{GTFS_ID}", params={"f": "json"}, timeout=60).json()
    r = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{GTFS_ID}/data", timeout=300)
    r.raise_for_status()
    if r.content[:2] != b"PK":
        raise RuntimeError("GTFS: odpoveď nie je ZIP.")
    zdroj = {
        "nazov": meta.get("title", "Cestovné poriadky MHD vo formáte GTFS"),
        "licencia": "CC BY 4.0",
        "url": f"https://data.bratislava.sk/datasets/{GTFS_ID}",
        "upravene": datetime.fromtimestamp(meta["modified"] / 1000, timezone.utc).date().isoformat() if meta.get("modified") else None,
    }
    return zipfile.ZipFile(io.BytesIO(r.content)), zdroj


def citaj(z: zipfile.ZipFile, nazov: str):
    with z.open(nazov) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))


def den(s: str) -> date:
    return datetime.strptime(s, "%Y%m%d").date()


def aktivne_sluzby(z: zipfile.ZipFile) -> tuple[date, set[str]]:
    kalendar = list(citaj(z, "calendar.txt")) if "calendar.txt" in z.namelist() else []
    vynimky: dict[date, dict[str, str]] = defaultdict(dict)
    if "calendar_dates.txt" in z.namelist():
        for r in citaj(z, "calendar_dates.txt"):
            vynimky[den(r["date"])][r["service_id"]] = r["exception_type"]
    od = max([den(k["start_date"]) for k in kalendar] + [date.today()]) if kalendar else date.today()
    do = max([den(k["end_date"]) for k in kalendar]) if kalendar else od + timedelta(days=60)
    nazvy_dni = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    # Pre každú stredu zistíme aktívne služby a vyberieme prvú s najčastejšou
    # kombináciou – tak sa vyhneme sviatkom a dňom s výnimočným poriadkom.
    stredy: list[tuple[date, frozenset[str]]] = []
    d = od
    while d <= do:
        if d.weekday() == 2:
            sluzby = {k["service_id"] for k in kalendar
                      if k[nazvy_dni[d.weekday()]] == "1" and den(k["start_date"]) <= d <= den(k["end_date"])}
            sluzby |= {s for s, t in vynimky.get(d, {}).items() if t == "1"}
            sluzby -= {s for s, t in vynimky.get(d, {}).items() if t == "2"}
            if sluzby:
                stredy.append((d, frozenset(sluzby)))
        d += timedelta(days=1)
    if not stredy:
        raise RuntimeError("GTFS: nenašiel som vhodný pracovný deň v období platnosti.")
    pocty: dict[frozenset[str], int] = defaultdict(int)
    for _, s in stredy:
        pocty[s] += 1
    typicke = max(pocty, key=lambda s: (pocty[s], len(s)))
    return next((d, set(s)) for d, s in stredy if s == typicke)


def main() -> int:
    z, zdroj = stiahni_gtfs()
    datum, sluzby = aktivne_sluzby(z)

    linky = {r["route_id"]: r for r in citaj(z, "routes.txt")}
    spoje = {r["trip_id"]: r["route_id"] for r in citaj(z, "trips.txt") if r["service_id"] in sluzby}

    stops = {r["stop_id"]: r for r in citaj(z, "stops.txt")}

    def zastavka(stop_id: str) -> str:
        s = stops[stop_id]
        return stops.get(s.get("parent_station") or "", s)["stop_name"].strip()

    # Zastavenia spojov v daný deň; posledné zastavenie spoja nie je odchod.
    posledne: dict[str, tuple[int, str]] = {}
    zastavenia = []
    for r in citaj(z, "stop_times.txt"):
        t = r["trip_id"]
        if t not in spoje:
            continue
        poradie = int(r["stop_sequence"])
        zastavenia.append((t, poradie, r["stop_id"]))
        if t not in posledne or poradie > posledne[t][0]:
            posledne[t] = (poradie, r["stop_id"])

    hranice = json.loads((DATA / "hranice-bratislava.geojson").read_text(encoding="utf-8"))
    obyv = json.loads((DATA / "obyvatelstvo-bratislava.json").read_text(encoding="utf-8"))
    rok = max(obyv["mesto"]["roky"])
    pocty_obyv = {c["kod"][-6:]: c["roky"][rok] for c in obyv["mestske_casti"]}
    casti = [(f["properties"]["kod_obce"], f["properties"]["nazov"], prep(shape(f["geometry"]))) for f in hranice["features"]]

    # Zastávky: zlúčenie platforiem podľa názvu, súradnice = priemer platforiem.
    body: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for sid, s in stops.items():
        if s.get("location_type", "0") in ("", "0") and s.get("stop_lat"):
            body[zastavka(sid)].append((float(s["stop_lat"]), float(s["stop_lon"])))

    def mc(lat: float, lon: float) -> str | None:
        p = Point(lon, lat)
        return next((kod for kod, _, g in casti if g.contains(p)), None)

    info: dict[str, dict] = {}
    for nazov, pts in body.items():
        lat = sum(p[0] for p in pts) / len(pts)
        lon = sum(p[1] for p in pts) / len(pts)
        info[nazov] = {"nazov": nazov, "lat": round(lat, 5), "lon": round(lon, 5), "kod_obce": mc(lat, lon),
                       "odchody": 0, "linky": set()}

    linky_druh: dict[str, set[str]] = defaultdict(set)
    odchody_druh: dict[str, int] = defaultdict(int)
    for t, poradie, stop_id in zastavenia:
        if posledne[t][0] == poradie:
            continue
        route = linky[spoje[t]]
        druh = DRUHY.get(route["route_type"], "Ostatné")
        meno = route["route_short_name"].strip()
        z_info = info.get(zastavka(stop_id))
        if z_info is None:
            continue
        z_info["odchody"] += 1
        z_info["linky"].add(meno)
        linky_druh[druh].add(meno)
        odchody_druh[druh] += 1

    v_ba = [i for i in info.values() if i["kod_obce"] and i["odchody"] > 0]
    po_castiach = []
    for kod, nazov, _ in casti:
        zz = [i for i in v_ba if i["kod_obce"] == kod]
        odch = sum(i["odchody"] for i in zz)
        obyv_mc = pocty_obyv.get(kod)
        po_castiach.append({
            "kod_obce": kod, "nazov": nazov, "zastavky": len(zz), "odchody": odch,
            "linky": len(set().union(*[i["linky"] for i in zz])) if zz else 0,
            "obyvatelia": obyv_mc,
            "odchody_na_1000": round(1000 * odch / obyv_mc, 1) if obyv_mc else None,
        })
    po_castiach.sort(key=lambda c: c["nazov"])

    zastavky = sorted(
        ({"nazov": i["nazov"], "lat": i["lat"], "lon": i["lon"], "kod_obce": i["kod_obce"], "odchody": i["odchody"],
          "linky": sorted(i["linky"], key=lambda x: (len(x), x))} for i in v_ba),
        key=lambda i: -i["odchody"],
    )
    if len(zastavky) < 300:
        raise RuntimeError(f"GTFS: podozrivo málo zastávok v Bratislave ({len(zastavky)}).")

    vystup = {
        "zdroj": zdroj,
        "den": datum.isoformat(),
        "platnost": {"od": next(citaj(z, "feed_info.txt"), {}).get("feed_start_date"),
                     "do": next(citaj(z, "feed_info.txt"), {}).get("feed_end_date")},
        "mesto": {
            "zastavky": len(zastavky),
            "odchody": sum(i["odchody"] for i in zastavky),
            "linky": {d: len(v) for d, v in sorted(linky_druh.items())},
            "odchody_druh": dict(sorted(odchody_druh.items())),
        },
        "mestske_casti": po_castiach,
        "zastavky": zastavky,
    }
    if VYSTUP.exists():
        stary = json.loads(VYSTUP.read_text(encoding="utf-8"))
        if {k: v for k, v in stary.items() if k not in ("aktualizovane", "den")} == {k: v for k, v in vystup.items() if k != "den"}:
            print("Doprava: bez zmeny")
            return 0
    vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    VYSTUP.write_text(json.dumps(vystup, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    m = vystup["mesto"]
    print(f"OK doprava {datum}: {m['zastavky']} zastávok, {m['odchody']} odchodov, linky {m['linky']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber dopravy::{type(e).__name__}: {sprava}")
        sys.exit(1)
