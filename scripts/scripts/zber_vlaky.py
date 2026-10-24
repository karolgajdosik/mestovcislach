"""Vlaky v krajských mestách – celoštátny cestovný poriadok (GTFS) zo Železníc SR.

Zdroj: Národný katalóg otvorených dát – „Grafikon vlakovej dopravy vo formáte GTFS“ (ŽSR), všetci dopravcovia
(ZSSK, RegioJet, Leo Express, ...). Odkaz na súbor zisťujeme cez SPARQL katalógu (mení sa pri novom grafikone).

Pre typický pracovný deň (najbližšia streda v platnosti grafikonu): odchody vlakov zo staníc mesta, dopravcovia
a priame spojenia medzi krajskými mestami (počet vlakov, najrýchlejší čas, prvý a posledný odchod).

Výstup: data/mesta/vlaky.json
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from spolocne import DATA, KOREN, s, spusti, zapis_ak_zmena

SPARQL = "https://data.slovensko.sk/api/sparql"
DATASET = "ebeeedf1-aca2-451a-bdc0-35d536714888"
ZALOHA = "https://data.slovensko.sk/download?id=fb3a9724-623b-4ddf-a6b5-a19b4a346281"
MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))
HLAVNA = {"bratislava": "Bratislava hl.st."}


def url_gtfs() -> str:
    q = ("PREFIX dcat:<http://www.w3.org/ns/dcat#> SELECT ?url WHERE { ?ds dcat:distribution ?d . ?d dcat:downloadURL ?url . "
         f'FILTER(CONTAINS(STR(?ds),"{DATASET}")) }}')
    try:
        r = s.get(SPARQL, params={"query": q}, headers={"Accept": "application/sparql-results+json"}, timeout=90).json()
        urls = [b["url"]["value"] for b in r["results"]["bindings"]]
        return next((u for u in urls if "data.slovensko.sk/download" in u), urls[0] if urls else ZALOHA)
    except Exception:  # noqa: BLE001
        return ZALOHA


def tabulka(zf: zipfile.ZipFile, nazov: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(zf.read(nazov).decode("utf-8-sig"))))


def sekundy(t: str) -> int:
    h, m, s_ = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s_


def hhmm(sek: int) -> str:
    return f"{(sek // 3600) % 24}:{(sek % 3600) // 60:02d}"


def main() -> int:
    url = url_gtfs()
    r = s.get(url, timeout=300)
    r.raise_for_status()
    if r.content[:2] != b"PK":
        raise RuntimeError(f"GTFS nie je ZIP ({url})")
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    info = (tabulka(zf, "feed_info.txt") or [{}])[0] if "feed_info.txt" in zf.namelist() else {}
    od = datetime.strptime(info.get("feed_start_date") or "20000101", "%Y%m%d").date()
    do = datetime.strptime(info.get("feed_end_date") or "20991231", "%Y%m%d").date()

    # typický pracovný deň: najbližšia streda v platnosti grafikonu (nie sviatok – vyberieme deň s najviac spojmi z dvoch stried)
    kalendar = tabulka(zf, "calendar.txt") if "calendar.txt" in zf.namelist() else []
    vynimky = tabulka(zf, "calendar_dates.txt") if "calendar_dates.txt" in zf.namelist() else []

    def sluzby(d: date) -> set[str]:
        ds, den = d.strftime("%Y%m%d"), ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][d.weekday()]
        akt = {c["service_id"] for c in kalendar if c["start_date"] <= ds <= c["end_date"] and c[den] == "1"}
        for v in vynimky:
            if v["date"] == ds:
                (akt.add if v["exception_type"] == "1" else akt.discard)(v["service_id"])
        return akt

    zaciatok = max(date.today() + timedelta(days=1), od)
    stredy = [zaciatok + timedelta(days=(2 - zaciatok.weekday()) % 7 + 7 * i) for i in range(3)]
    stredy = [d for d in stredy if d <= do] or [zaciatok]
    trips_all = tabulka(zf, "trips.txt")
    den = max(stredy, key=lambda d: sum(1 for t in trips_all if t["service_id"] in sluzby(d)))
    akt = sluzby(den)
    trips = {t["trip_id"]: t for t in trips_all if t["service_id"] in akt}
    routes = {r_["route_id"]: r_ for r_ in tabulka(zf, "routes.txt")}
    agencies = {a["agency_id"]: a["agency_name"].replace(", a.s.", "").replace(",a.s.", "").strip() for a in tabulka(zf, "agency.txt")}
    stops = {x["stop_id"]: x["stop_name"] for x in tabulka(zf, "stops.txt")}

    # stanice miest: presný názov mesta alebo „Mesto …“ / „Mesto-…“
    stanice = {m["slug"]: {sid for sid, n in stops.items() if n == m["nazov"] or n.startswith(m["nazov"] + " ") or n.startswith(m["nazov"] + "-")} for m in MESTA}
    hlavna = {m["slug"]: next((sid for sid in stanice[m["slug"]] if stops[sid] == HLAVNA.get(m["slug"], m["nazov"])), None) for m in MESTA}
    mesto_stanice = {sid: slug for slug, ids in stanice.items() for sid in ids}

    zastavenia: dict[str, list] = defaultdict(list)
    for st in tabulka(zf, "stop_times.txt"):
        if st["trip_id"] in trips:
            zastavenia[st["trip_id"]].append((int(st["stop_sequence"]), st["stop_id"], st["arrival_time"] or st["departure_time"], st["departure_time"] or st["arrival_time"]))

    vysl = {m["slug"]: {"stanice": sorted(stops[x] for x in stanice[m["slug"]]), "hlavna": stops.get(hlavna[m["slug"]] or "", None),
                        "odchodov": 0, "odchodov_hlavna": 0, "dopravcovia": defaultdict(int), "spojenia": {}} for m in MESTA}
    spojenia: dict[tuple, list] = defaultdict(list)
    for tid, zz in zastavenia.items():
        zz.sort()
        dopravca = agencies.get(routes.get(trips[tid]["route_id"], {}).get("agency_id", ""), "")
        prve: dict[str, tuple] = {}  # mesto → (index, odchod) prvého zastavenia v meste
        for i, (_, sid, prich, odch) in enumerate(zz):
            slug = mesto_stanice.get(sid)
            if not slug:
                continue
            if i < len(zz) - 1:
                vysl[slug]["odchodov"] += 1
                vysl[slug]["dopravcovia"][dopravca] += 1
                if sid == hlavna[slug]:
                    vysl[slug]["odchodov_hlavna"] += 1
            # priame spojenie: z ktoréhokoľvek skoršieho mesta do tohto
            for z_slug, (z_i, z_odch) in prve.items():
                if z_slug != slug:
                    spojenia[(z_slug, slug)].append((sekundy(prich) - sekundy(z_odch), sekundy(z_odch)))
            if slug not in prve and i < len(zz) - 1:
                prve[slug] = (i, odch)
    for (a, b), x in spojenia.items():
        # jeden vlak sa môže zarátať viackrát (viac staníc v meste) – berieme unikátne odchody
        odchody = sorted({o for _, o in x})
        vysl[a]["spojenia"][b] = {"vlakov": len(odchody), "najrychlejsie_min": round(min(t for t, _ in x) / 60), "prvy": hhmm(odchody[0]), "posledny": hhmm(odchody[-1])}
    for v in vysl.values():
        v["dopravcovia"] = dict(sorted(v["dopravcovia"].items(), key=lambda kv: -kv[1]))
    print(f"Deň {den}: {len(trips)} vlakov; " + ", ".join(f"{k} {v['odchodov']} odchodov, {len(v['spojenia'])} miest" for k, v in vysl.items()))
    if sum(v["odchodov"] for v in vysl.values()) < 200:
        raise RuntimeError("Vlaky: podozrivo málo odchodov")
    zapis_ak_zmena(DATA / "mesta" / "vlaky.json", {
        "zdroj": {"nazov": "Železnice SR – grafikon vlakovej dopravy (GTFS), Národný katalóg otvorených dát", "url": f"https://data.slovensko.sk/datasety/{DATASET}"},
        "den": den.isoformat(), "platnost": [od.isoformat(), do.isoformat()], "vlakov_v_den": len(trips), "mesta": vysl,
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return 0


if __name__ == "__main__":
    spusti(main, "Vlaky krajských miest (GTFS)")
