"""Železničné stanice a zastávky v obciach a počet vlakov za bežný pracovný deň.

Zdroj: ŽSR – Grafikon vlakovej dopravy vo formáte GTFS (Národný katalóg otvorených dát, data.slovensko.sk,
dataset ebeeedf1-aca2-451a-bdc0-35d536714888). Stanica sa priradí k obci podľa názvu (začiatok názvu stanice
= názov obce, skratky n./p. rozpísané) a pri viacerých obciach rovnakého mena podľa polohy; bez zhody názvu
podľa hraníc obcí v OpenStreetMap (tag ref = kód obce; výsledok sa ukladá do vlaky_stanice.json).

Výstup data/obce/vlaky.json: {"den": dátum, "obce": {kód: [[stanica, vlakov za deň], …]}}
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE, PODLA_NAZVU, kluc

DATASET = "ebeeedf1-aca2-451a-bdc0-35d536714888"
POL = {o["kod"]: o.get("poloha") for o in OBCE}


ZALOHA = "https://www.zsr.sk/files/pre-cestujucich/cestovny-poriadok/gtfs/gtfs.zip"


def gtfs_urls() -> list[str]:
    """Odkazy na súbor GTFS: distribúcie datasetu z SPARQL endpointu katalógu (stránka je JS aplikácia), záložne ŽSR."""
    q = ("PREFIX dcat:<http://www.w3.org/ns/dcat#> SELECT ?u WHERE { ?ds dcat:distribution ?d . ?d dcat:downloadURL ?u . "
         f'FILTER(CONTAINS(STR(?ds),"{DATASET}")) }}')
    out: list[str] = []
    try:
        r = s.get("https://data.slovensko.sk/api/sparql", params={"query": q}, headers={"Accept": "application/sparql-results+json"}, timeout=90)
        r.raise_for_status()
        out = [b["u"]["value"] for b in r.json()["results"]["bindings"]]
    except Exception as e:  # noqa: BLE001
        print(f"  SPARQL katalógu: {e}")
    return out + [ZALOHA]


def stiahni_gtfs() -> tuple[str, zipfile.ZipFile]:
    chyby = []
    for u in gtfs_urls():
        try:
            r = s.get(u, timeout=300)
            r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content))
            if "stop_times.txt" in z.namelist():
                return u, z
            chyby.append(f"{u}: nie je GTFS")
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{u}: {e}")
    raise RuntimeError("GTFS sa nepodarilo stiahnuť: " + "; ".join(chyby))


def citaj(z: zipfile.ZipFile, n: str) -> list[dict]:
    if n not in z.namelist():
        return []
    return list(csv.DictReader(io.StringIO(z.read(n).decode("utf-8-sig", "replace"))))


def den_prevadzky(z: zipfile.ZipFile) -> tuple[date, set[str]]:
    """Najbližšia streda (bežný pracovný deň), v ktorú cestovný poriadok platí; množina service_id."""
    cal = citaj(z, "calendar.txt")
    dates = citaj(z, "calendar_dates.txt")
    d = date.today()
    for _ in range(120):
        d += timedelta(days=1)
        if d.weekday() != 2:
            continue
        ds = d.strftime("%Y%m%d")
        sluzby = {c["service_id"] for c in cal if c.get("start_date", "") <= ds <= c.get("end_date", "") and c.get("wednesday") == "1"}
        for x in dates:
            if x["date"] == ds:
                (sluzby.add if x["exception_type"] == "1" else sluzby.discard)(x["service_id"])
        if len(sluzby) > 5:
            return d, sluzby
    raise RuntimeError("GTFS: nenašiel sa deň, v ktorý cestovný poriadok platí")


SKRATKY = [(r"\bn\.\s*", "nad "), (r"\bp\.\s*", "pod "), (r"\bN\.\s*", "Nová "), (r"\bSt\.\s*", "Stará "), (r"\bSv\.\s*", "Svätý "),
           (r"\bRim\.\s*", "Rimavicou ")]
KODY = set(POL)
NAZOV_KOD = {kluc(o["nazov"]): o["kod"] for o in OBCE if o["nazov"] in ("Bratislava", "Košice")}
CACHE = DATA / "obce" / "vlaky_stanice.json"  # stop_id -> kód obce z hraníc OSM (verejná infraštruktúra, bez osobných údajov)


def obec_podla_nazvu(nazov: str, lat: float, lon: float) -> str | None:
    n = nazov
    for vz, nah in SKRATKY:
        n = re.sub(vz, nah, n)
    k = kluc(re.sub(r"\b(os\.\s*st\.|osobná stanica|zastávka|zast\.|žst\.|hl\.\s*st\.|stanica)", "", n, flags=re.I))
    slova = k.replace("-", " ").split()
    for dl in range(len(slova), 0, -1):  # najdlhší začiatok názvu, ktorý je obcou
        kand = PODLA_NAZVU.get(" ".join(slova[:dl]), []) or PODLA_NAZVU.get("-".join(slova[:dl]), [])
        kand = [k_ for k_ in kand if POL.get(k_)]
        if kand:
            best = min(kand, key=lambda k_: math.dist(POL[k_], (lat, lon)))
            return best if math.dist(POL[best], (lat, lon)) < 0.12 else None  # ~10 km
    return None


def obec_podla_osm(lat: float, lon: float) -> str | None:
    """Obec, v ktorej hraniciach stanica leží (OSM, tag ref = kód obce); mestské časti -> mesto."""
    q = f'[out:json][timeout:60];is_in({lat},{lon})->.a;area.a[boundary=administrative][admin_level~"^([4-9]|10)$"];out tags;'
    for pokus in range(4):
        try:
            r = s.post("https://overpass-api.de/api/interpreter", data={"data": q}, timeout=90)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(10 * (pokus + 1))
                continue
            r.raise_for_status()
            oblasti = [e["tags"] for e in r.json().get("elements", [])]
            for tg in sorted(oblasti, key=lambda tg: -int(tg.get("admin_level", 0))):
                if tg.get("ref") in KODY:
                    return tg["ref"]
            for tg in oblasti:
                for nk, kod in NAZOV_KOD.items():
                    if kluc(tg.get("name", "")).startswith(nk):
                        return kod
            return ""
        except Exception as e:  # noqa: BLE001
            print(f"  OSM {lat},{lon}: {e}")
            time.sleep(5)
    return None


def main() -> int:
    url, z = stiahni_gtfs()
    print(f"GTFS: {url}")
    den, sluzby = den_prevadzky(z)
    trips = {t["trip_id"] for t in citaj(z, "trips.txt") if t["service_id"] in sluzby}
    stops = {x["stop_id"]: x for x in citaj(z, "stops.txt")}
    rodic = {sid: (x.get("parent_station") or sid) for sid, x in stops.items()}
    vlaky: dict[str, set] = defaultdict(set)
    for st in citaj(z, "stop_times.txt"):
        if st["trip_id"] in trips:
            vlaky[rodic.get(st["stop_id"], st["stop_id"])].add(st["trip_id"])
    obce: dict[str, list] = defaultdict(list)
    bez = osm = 0
    cache: dict[str, str] = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    nepr: list[str] = []
    print(f"Staníc s vlakmi: {len(vlaky)}, záznamov v stops.txt: {len(stops)}")
    for sid, tr in vlaky.items():
        x = stops.get(sid)
        if not x:
            continue
        try:
            lat, lon = float(x["stop_lat"]), float(x["stop_lon"])
        except (KeyError, ValueError):
            continue
        if not sid.startswith("56") or not (47.6 < lat < 49.7 and 16.8 < lon < 22.6):
            continue  # stanice v zahraničí (UIC kód krajiny SK = 56)
        kod = obec_podla_nazvu(x["stop_name"], lat, lon)
        if not kod:
            if sid not in cache:
                v = obec_podla_osm(lat, lon)
                if v is not None:
                    cache[sid] = v
                time.sleep(1)
            kod = cache.get(sid) or None
            if kod:
                osm += 1
        if not kod:
            bez += 1
            nepr.append(x["stop_name"].strip())
            continue
        obce[kod].append([x["stop_name"].strip(), len(tr)])
    for v in obce.values():
        v.sort(key=lambda a: -a[1])
    zapis_ak_zmena(CACHE, dict(sorted(cache.items())), kompaktne=True)
    print(f"  podľa hraníc OSM priradených {osm}")
    if nepr:
        print("  nepriradené stanice (ukážka):", "; ".join(sorted(nepr)[:60]))
    if len(obce) < 450:
        raise RuntimeError(f"GTFS: len {len(obce)} obcí so stanicou")
    zapis_ak_zmena(DATA / "obce" / "vlaky.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "den": den.isoformat(),
        "zdroj": {"nazov": "ŽSR – Grafikon vlakovej dopravy (GTFS), Národný katalóg otvorených dát", "url": f"https://data.slovensko.sk/datasety/{DATASET}"},
        "obce": dict(sorted(obce.items()))}, kompaktne=True)
    print(f"Vlaky {den}: {len(obce)} obcí so stanicou, nepriradených staníc {bez}")
    return 0


if __name__ == "__main__":
    spusti(main, "Vlaky v obciach (GTFS ŽSR)")
