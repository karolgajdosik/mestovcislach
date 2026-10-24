"""MHD v Prešove – cestovný poriadok DPMP vo formáte GTFS (mesto Prešov, ArcGIS Online, licencia CC BY 4.0).

Pre typický pracovný deň (najbližší pracovný deň v platnosti s najviac spojmi; ak grafikon ešte nemá budúce dni,
posledný pracovný deň v platnosti): linky (autobus/trolejbus) a počet spojov, zastávky (zlúčené podľa názvu)
s počtom odchodov a linkami, odchody podľa hodín.

Výstup: data/mesta/mhd-presov.json
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from datetime import date, datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena

POLOZKA = "f1033ca6c2f4461d9aba285e1c7cb079"
URL = f"https://www.arcgis.com/sharing/rest/content/items/{POLOZKA}/data"
TYP = {"0": "električka", "3": "autobus", "11": "trolejbus", "800": "trolejbus"}


def tabulka(zf: zipfile.ZipFile, nazov: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(zf.read(nazov).decode("utf-8-sig")))) if nazov in zf.namelist() else []


def main() -> int:
    r = s.get(URL, timeout=300)
    r.raise_for_status()
    if r.content[:2] != b"PK":
        raise RuntimeError("GTFS Prešov nie je ZIP")
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    info = (tabulka(zf, "feed_info.txt") or [{}])[0]
    kalendar = tabulka(zf, "calendar.txt")
    vynimky = tabulka(zf, "calendar_dates.txt")
    trips_all = tabulka(zf, "trips.txt")

    # aktívne služby po dňoch (calendar + calendar_dates)
    dni: dict[str, set[str]] = defaultdict(set)
    DNI = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for c in kalendar:
        od, do = datetime.strptime(c["start_date"], "%Y%m%d").date(), datetime.strptime(c["end_date"], "%Y%m%d").date()
        d = od
        while d <= do:
            if c[DNI[d.weekday()]] == "1":
                dni[d.strftime("%Y%m%d")].add(c["service_id"])
            d = date.fromordinal(d.toordinal() + 1)
    for v in vynimky:
        (dni[v["date"]].add if v["exception_type"] == "1" else dni[v["date"]].discard)(v["service_id"])
    spoje_v_den = {d: sum(1 for t in trips_all if t["service_id"] in sl) for d, sl in dni.items()}
    pracovne = [d for d in spoje_v_den if datetime.strptime(d, "%Y%m%d").weekday() < 5 and spoje_v_den[d]]
    if not pracovne:
        raise RuntimeError("GTFS Prešov: žiadny pracovný deň so spojmi")
    dnes = date.today().strftime("%Y%m%d")
    buduce = [d for d in pracovne if d >= dnes]
    kandidati = buduce[:10] if buduce else sorted(pracovne)[-10:]
    den = max(sorted(kandidati), key=lambda d: spoje_v_den[d])
    akt = dni[den]

    routes = {x["route_id"]: x for x in tabulka(zf, "routes.txt")}
    trips = {t["trip_id"]: t for t in trips_all if t["service_id"] in akt}
    stops = {x["stop_id"]: x for x in tabulka(zf, "stops.txt")}

    linka = lambda rid: routes.get(rid, {}).get("route_short_name") or rid  # noqa: E731
    odchody: dict[str, int] = defaultdict(int)
    linky_zast: dict[str, set[str]] = defaultdict(set)
    hodiny = [0] * 24
    posledna: dict[str, tuple[int, str]] = {}
    for st in tabulka(zf, "stop_times.txt"):
        t = trips.get(st["trip_id"])
        if not t:
            continue
        seq = int(st["stop_sequence"])
        # posledné zastavenie spoja nie je odchod – zapamätáme si ho a odpočítame
        if st["trip_id"] not in posledna or seq > posledna[st["trip_id"]][0]:
            posledna[st["trip_id"]] = (seq, st["stop_id"])
        odchody[st["stop_id"]] += 1
        linky_zast[st["stop_id"]].add(linka(t["route_id"]))
        cas = st["departure_time"] or st["arrival_time"]
        if cas:
            hodiny[int(cas.split(":")[0]) % 24] += 1
    for _, sid in posledna.values():
        odchody[sid] -= 1

    # zastávky zlúčené podľa názvu (nástupištia toho istého mena), poloha = priemer nástupíšť
    zast: dict[str, dict] = {}
    for sid, n in odchody.items():
        x = stops.get(sid)
        if not x:
            continue
        z = zast.setdefault(x["stop_name"].strip(), {"lat": [], "lon": [], "odchody": 0, "linky": set()})
        z["lat"].append(float(x["stop_lat"]))
        z["lon"].append(float(x["stop_lon"]))
        z["odchody"] += max(0, n)
        z["linky"] |= linky_zast[sid]
    poradie = lambda l: (not l.isdigit(), int(l) if l.isdigit() else 0, l)  # noqa: E731
    zastavky = sorted(({"nazov": k, "lat": round(sum(v["lat"]) / len(v["lat"]), 5), "lon": round(sum(v["lon"]) / len(v["lon"]), 5),
                        "odchody": v["odchody"], "linky": sorted(v["linky"], key=poradie)} for k, v in zast.items()), key=lambda z: -z["odchody"])

    spoje_linky: dict[str, int] = defaultdict(int)
    for t in trips.values():
        spoje_linky[t["route_id"]] += 1
    linky = sorted(({"linka": linka(rid), "nazov": routes[rid].get("route_long_name", ""), "typ": TYP.get(routes[rid].get("route_type", "3"), "autobus"), "spojov": n}
                    for rid, n in spoje_linky.items() if rid in routes), key=lambda x: poradie(x["linka"]))
    print(f"Deň {den}: {len(trips)} spojov, {len(linky)} liniek, {len(zastavky)} zastávok; najviac odchodov: {zastavky[0]['nazov']} {zastavky[0]['odchody']}")
    if len(trips) < 300 or len(zastavky) < 100:
        raise RuntimeError("MHD Prešov: podozrivo málo spojov alebo zastávok")
    zapis_ak_zmena(DATA / "mesta" / "mhd-presov.json", {
        "zdroj": {"nazov": "Mesto Prešov – GTFS MHD Prešov (Dopravný podnik mesta Prešov), CC BY 4.0", "url": f"https://www.arcgis.com/home/item.html?id={POLOZKA}"},
        "den": datetime.strptime(den, "%Y%m%d").date().isoformat(),
        "platnost": [info.get("feed_start_date"), info.get("feed_end_date")],
        "spolu": {"spojov": len(trips), "liniek": len(linky), "zastavok": len(zastavky), "odchodov": sum(z["odchody"] for z in zastavky),
                  "trolejbusovych": sum(1 for l in linky if l["typ"] == "trolejbus")},
        "hodiny": hodiny, "linky": linky, "zastavky": zastavky,
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return 0


if __name__ == "__main__":
    spusti(main, "MHD Prešov (GTFS)")
