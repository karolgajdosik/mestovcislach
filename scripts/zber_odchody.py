"""Odchody MHD zo zastávok – cestovné poriadky GTFS (Bratislava – DPB, Prešov – DPMP; obe CC BY 4.0).

Pre každú zastávku (nástupištia zlúčené podľa názvu) uloží všetky odchody podľa služby (service_id) a kalendár,
ktoré služby premávajú v ktorý deň. Prehliadač si podľa dnešného dátumu vyberie správne spoje.
Košice zverejňujú len zastaraný export JDF (platnosť liniek 2022 – 2024), preto tu nie sú.

Výstup: data/odchody/<mesto>.json (kompaktný; stránky po zastávkach generuje Astro: src/pages/data/odchody/)
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena

ZDROJE = {
    "bratislava": ("aba12fd2cbac4843bc7406151bc66106", "Dopravný podnik Bratislava – cestovné poriadky MHD (GTFS), data.bratislava.sk", "https://data.bratislava.sk/datasets/aba12fd2cbac4843bc7406151bc66106"),
    "presov": ("f1033ca6c2f4461d9aba285e1c7cb079", "Mesto Prešov – GTFS MHD Prešov (Dopravný podnik mesta Prešov)", "https://www.arcgis.com/home/item.html?id=f1033ca6c2f4461d9aba285e1c7cb079"),
}
TYP = {"0": "električka", "900": "električka", "11": "trolejbus", "800": "trolejbus", "3": "autobus", "700": "autobus", "2": "vlak", "4": "loď"}
DNI = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
VYSTUP = DATA / "odchody"


def slug(t: str) -> str:
    t = unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "zastavka"


def citaj(z: zipfile.ZipFile, nazov: str) -> list[dict]:
    if nazov not in z.namelist():
        return []
    return list(csv.DictReader(io.StringIO(z.read(nazov).decode("utf-8-sig"))))


def cas(t: str) -> int:
    h, m, *_ = t.strip().split(":")
    return int(h) * 60 + int(m)


def den(x: str) -> date:
    return datetime.strptime(x, "%Y%m%d").date()


def mesto(slug_mesta: str, polozka: str, nazov: str, url: str) -> dict:
    meta = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{polozka}", params={"f": "json"}, timeout=60).json()
    r = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{polozka}/data", timeout=300)
    r.raise_for_status()
    if r.content[:2] != b"PK":
        raise RuntimeError("GTFS: odpoveď nie je ZIP")
    z = zipfile.ZipFile(io.BytesIO(r.content))

    # --- kalendár: ktoré služby premávajú v ktorý deň ---
    kal = citaj(z, "calendar.txt")
    vyn: dict[date, dict[str, str]] = defaultdict(dict)
    for x in citaj(z, "calendar_dates.txt"):
        vyn[den(x["date"])][x["service_id"]] = x["exception_type"]
    dni_vsetky = [den(k["start_date"]) for k in kal] + [den(k["end_date"]) for k in kal] + list(vyn)
    if not dni_vsetky:
        raise RuntimeError("GTFS bez kalendára")
    od, do = min(dni_vsetky), max(dni_vsetky)

    def sluzby_dna(d: date) -> frozenset[str]:
        a = {k["service_id"] for k in kal if k[DNI[d.weekday()]] == "1" and den(k["start_date"]) <= d <= den(k["end_date"])}
        a |= {sid for sid, t in vyn.get(d, {}).items() if t == "1"}
        a -= {sid for sid, t in vyn.get(d, {}).items() if t == "2"}
        return frozenset(a)

    vsetky_dni = {}
    d = od
    while d <= do:
        vsetky_dni[d] = sluzby_dna(d)
        d += timedelta(days=1)

    # --- spoje a odchody ---
    stops = {x["stop_id"]: x for x in citaj(z, "stops.txt")}
    routes = {x["route_id"]: x for x in citaj(z, "routes.txt")}
    trips = {x["trip_id"]: x for x in citaj(z, "trips.txt")}
    st_rows = citaj(z, "stop_times.txt")
    po_spoji: dict[str, list[tuple[int, str, str, str]]] = defaultdict(list)
    for x in st_rows:
        t = x.get("departure_time") or x.get("arrival_time")
        if not t or x["trip_id"] not in trips:
            continue
        po_spoji[x["trip_id"]].append((int(x["stop_sequence"]), x["stop_id"], t, x.get("pickup_type", "0") or "0"))

    def cisty(n: str) -> str:  # „Bardejovská  *“ (zastávka na znamenie) → „Bardejovská“
        return re.sub(r"\s*\*+$", "", re.sub(r"\s+", " ", n)).strip()

    def nazov_zast(sid: str) -> str:
        z_ = stops.get(sid, {})
        par = z_.get("parent_station")
        if par and par in stops:
            return cisty(stops[par]["stop_name"])
        return cisty(z_.get("stop_name", sid))

    linky: list[list[str]] = []
    linky_idx: dict[str, int] = {}
    smery: list[str] = []
    smery_idx: dict[str, int] = {}
    sluzby: list[str] = []
    sluzby_idx: dict[str, int] = {}

    def idx(zoznam, mapa, kluc, hodnota):
        if kluc not in mapa:
            mapa[kluc] = len(zoznam)
            zoznam.append(hodnota)
        return mapa[kluc]

    pouzite_sluzby = {t["service_id"] for t in trips.values()}
    odchody: dict[str, dict[tuple[int, int, int], list[int]]] = defaultdict(lambda: defaultdict(list))
    body: dict[str, list[tuple[float, float]]] = defaultdict(list)
    linky_zast: dict[str, set[int]] = defaultdict(set)
    for tid, zast in po_spoji.items():
        zast.sort()
        tr = trips[tid]
        ro = routes.get(tr["route_id"], {})
        meno = (ro.get("route_short_name") or ro.get("route_long_name") or "?").strip()
        li = idx(linky, linky_idx, tr["route_id"], [meno, TYP.get(ro.get("route_type", ""), "autobus"), (ro.get("route_color") or "").strip(), (ro.get("route_text_color") or "").strip()])
        smer = cisty(tr.get("trip_headsign") or "") or nazov_zast(zast[-1][1])
        hi = idx(smery, smery_idx, smer, smer)
        si = idx(sluzby, sluzby_idx, tr["service_id"], tr["service_id"])
        for _, sid, t, pick in zast[:-1]:  # posledná zastávka spoja = len príchod
            if pick == "1":
                continue
            n = nazov_zast(sid)
            if n == smer:
                continue
            odchody[n][(li, hi, si)].append(cas(t))
            linky_zast[n].add(li)
    for sid, x in stops.items():
        if x.get("location_type", "0") in ("", "0") and x.get("stop_lat"):
            body[nazov_zast(sid)].append((float(x["stop_lat"]), float(x["stop_lon"])))

    # --- zastávky: id podľa názvu ---
    zastavky, ids, out_odch = [], set(), {}
    for n in sorted(odchody, key=lambda v: slug(v)):
        b = body.get(n)
        if not b:
            continue
        i = slug(n)
        while i in ids:
            i += "-2"
        ids.add(i)
        lat, lon = sum(p[0] for p in b) / len(b), sum(p[1] for p in b) / len(b)
        zastavky.append({"id": i, "n": n, "lat": round(lat, 5), "lon": round(lon, 5), "l": sorted(linky_zast[n], key=lambda k: (linky[k][1], len(linky[k][0]), linky[k][0]))})
        vzory = []
        for (li, hi, si), casy in sorted(odchody[n].items()):
            casy.sort()
            delty = [casy[0]] + [b_ - a for a, b_ in zip(casy, casy[1:])]
            vzory.append([li, hi, si, ",".join(map(str, delty))])
        out_odch[i] = vzory

    # --- kalendár celej platnosti (súbor sa tak mení len s novým poriadkom) + typický deň pre každý deň v týždni,
    #     ktorý prehliadač použije, ak dnešok v platnosti nie je ---
    sl = lambda fs: sorted(sluzby_idx[x] for x in fs if x in sluzby_idx)
    kalendar = {d.strftime("%Y%m%d"): sl(v) for d, v in vsetky_dni.items() if v & pouzite_sluzby}
    typicke = {}
    for w in range(7):
        kand = [(d, v) for d, v in vsetky_dni.items() if d.weekday() == w and v & pouzite_sluzby]
        if kand:
            naj = Counter(v for _, v in kand).most_common(1)[0][0]
            typicke[str(w + 1)] = next(d for d, v in kand if v == naj).strftime("%Y%m%d")
    dos = dosah(zastavky, po_spoji, trips, vsetky_dni, typicke, nazov_zast)
    pocet = sum(len(c.split(",")) for v in out_odch.values() for *_, c in v)
    if len(zastavky) < 50 or pocet < 5000:
        raise RuntimeError(f"podozrivo málo dát: {len(zastavky)} zastávok, {pocet} odchodov")
    print(f"  {slug_mesta}: {len(zastavky)} zastávok, {len(linky)} liniek, {len(sluzby)} služieb, {pocet} odchodov, platnosť {od}–{do}")
    return {
        "zdroj": {"nazov": nazov, "url": url, "licencia": "CC BY 4.0",
                  "upravene": datetime.fromtimestamp(meta["modified"] / 1000, timezone.utc).date().isoformat() if meta.get("modified") else None},
        "platnost": [od.isoformat(), do.isoformat()],
        "linky": linky, "smery": smery, "zastavky": zastavky, "kalendar": kalendar, "typicke": typicke, "odchody": out_odch,
    }, dos


# --- dosah MHD: kam sa dostanem zo zastávky za 15 / 30 / 45 / 60 minút (pracovný deň ráno) ---
STARTY = [8 * 60, 8 * 60 + 7, 8 * 60 + 15, 8 * 60 + 22]  # priemer cez viac časov odchodu, aby nerozhodla náhoda čakania
HORIZONT = 60
PESO_MAX = 400  # m – prestup pešo medzi blízkymi zastávkami


def dosah(zastavky, po_spoji, trips, vsetky_dni, typicke, nazov_zast) -> dict:
    """Connection Scan: najskorší príchod na každú zastávku pri odchode z každej zastávky. Výstup: pre každú
    zastávku reťazec minút (znak chr(48 + min), „~“ = viac ako hodina), poradie ako v zoznam zastávok."""
    from math import asin, ceil, cos, radians, sin, sqrt
    den_ = datetime.strptime(typicke.get("3") or next(iter(typicke.values())), "%Y%m%d").date()
    aktivne = vsetky_dni.get(den_, frozenset())
    idx = {z["n"]: i for i, z in enumerate(zastavky)}
    n = len(zastavky)
    od, do = min(STARTY), max(STARTY) + HORIZONT
    conns = []  # (odchod, príchod, z, do, spoj)
    for ti, (tid, zast) in enumerate(po_spoji.items()):
        if trips[tid]["service_id"] not in aktivne:
            continue
        body_ = [(idx.get(nazov_zast(sid)), cas(t)) for _, sid, t, _ in zast]
        for (a, ta), (b, tb) in zip(body_, body_[1:]):
            if a is None or b is None or a == b or ta < od or ta > do:
                continue
            conns.append((ta, tb, a, b, ti))
    conns.sort()

    def vzd(p, q):
        la1, lo1, la2, lo2 = map(radians, (p["lat"], p["lon"], q["lat"], q["lon"]))
        return 2 * 6371000 * asin(sqrt(sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2))

    pesi = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if abs(zastavky[i]["lat"] - zastavky[j]["lat"]) > 0.005:
                continue
            m = vzd(zastavky[i], zastavky[j])
            if m <= PESO_MAX:
                w = max(1, ceil(m * 1.3 / 80))
                pesi[i].append((j, w))
                pesi[j].append((i, w))
    INF = 10 ** 9
    riadky = []
    for o in range(n):
        sucet = [0] * n
        pocet = [0] * n
        for t0 in STARTY:
            e = [INF] * n
            e[o] = t0
            for j, w in pesi[o]:
                e[j] = min(e[j], t0 + w)
            v_spoji: set[int] = set()
            koniec = t0 + HORIZONT
            for ta, tb, a, b, ti in conns:
                if ta < t0:
                    continue
                if ta > koniec:
                    break
                if ti in v_spoji or e[a] <= ta:
                    v_spoji.add(ti)
                    if tb < e[b]:
                        e[b] = tb
                        for j, w in pesi[b]:
                            if tb + w < e[j]:
                                e[j] = tb + w
            for i in range(n):
                if e[i] - t0 <= HORIZONT:
                    sucet[i] += e[i] - t0
                    pocet[i] += 1
        # zastávka sa počíta, ak je dosiahnuteľná aspoň pri polovici časov odchodu
        riadky.append("".join(chr(48 + round(sucet[i] / pocet[i])) if pocet[i] * 2 >= len(STARTY) else "~" for i in range(n)))
    print(f"  dosah: {n} zastávok, {len(conns)} spojení, deň {den_}")
    return {"den": den_.isoformat(), "starty": STARTY, "horizont": HORIZONT, "ids": [z["id"] for z in zastavky], "r": riadky}


def main() -> int:
    VYSTUP.mkdir(parents=True, exist_ok=True)
    chyby = 0
    for slug_mesta, (polozka, nazov, url) in ZDROJE.items():
        try:
            d, dos = mesto(slug_mesta, polozka, nazov, url)
            zapis_ak_zmena(VYSTUP / f"{slug_mesta}.json", d, kompaktne=True)
            zapis_ak_zmena(DATA / "dosah" / f"{slug_mesta}.json", dos, kompaktne=True)
        except Exception as e:  # noqa: BLE001 – ostatné mestá pokračujú, uložené dáta ostávajú
            chyby += 1
            print(f"::warning title=Odchody MHD – {slug_mesta}::{type(e).__name__}: {e}")
    return 1 if chyby == len(ZDROJE) else 0


if __name__ == "__main__":
    spusti(main, "Odchody MHD (GTFS)")
