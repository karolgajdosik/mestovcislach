"""Klíma obcí za posledných 10 ukončených rokov – Open-Meteo (reanalýza ERA5, mriežka 0,25°) → data/obce/klima.json.

Pre každú bunku mriežky sa stiahnu denné hodnoty (teplota priemerná/max/min, zrážky, sneženie) a pre obce v bunke
sa vypočítajú ročné priemery. Teploty sa prepočítajú na nadmorskú výšku obce (z wiki.json) gradientom
−0,65 °C na 100 m – bunka ERA5 má jednu priemernú výšku (napr. 359 m) a obce v nej ležia vyššie aj nižšie.
Zrážky sa neprepočítavajú (sú to hodnoty bunky ~25 × 18 km).

Bezplatné API Open-Meteo počíta dlhé dotazy ako viac volaní (10 rokov ≈ 260), limit je 5 000 za hodinu
a 10 000 za deň – preto sa v jednom behu stiahne najviac BUNIEK_NA_BEH buniek a výsledok sa ukladá priebežne.
Workflow obce-klima.yml beží každé 3 hodiny, kým nie sú hotové všetky bunky; potom raz ročne pri novom roku.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date, datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE, median

SUBOR = DATA / "obce" / "klima.json"
BUNIEK_NA_BEH = 15
GRAD = -0.0065  # °C na meter
UA = {"User-Agent": "mestovcislach.sk (info@mestovcislach.sk)"}


def bunka(lat: float, lon: float) -> str:
    return f"{round(lat * 4) / 4:.2f},{round(lon * 4) / 4:.2f}"


def main() -> int:
    rok_do = date.today().year - 1
    rok_od = rok_do - 9
    obdobie = f"{rok_od}–{rok_do}"
    stare = json.loads(SUBOR.read_text(encoding="utf-8")) if SUBOR.exists() else {}
    if stare.get("obdobie") != obdobie:
        stare = {}
    obce: dict[str, list] = stare.get("obce", {})
    hotove: set[str] = set(stare.get("bunky", []))
    vysky = {}
    w = DATA / "obce" / "wiki.json"
    if w.exists():
        vysky = {k: v[1] for k, v in json.loads(w.read_text(encoding="utf-8"))["obce"].items() if v[1]}
    podla_bunky: dict[str, list[dict]] = defaultdict(list)
    for o in OBCE:
        if o.get("poloha"):
            podla_bunky[bunka(*o["poloha"])].append(o)
    zostava = sorted(b for b in podla_bunky if b not in hotove)
    print(f"Klíma {obdobie}: buniek {len(podla_bunky)}, hotových {len(hotove)}, zostáva {len(zostava)}")
    stiahnute = 0
    for b in zostava[:BUNIEK_NA_BEH]:
        lat, lon = map(float, b.split(","))
        r = s.get("https://archive-api.open-meteo.com/v1/archive", headers=UA, timeout=180, params={
            "latitude": lat, "longitude": lon, "start_date": f"{rok_od}-01-01", "end_date": f"{rok_do}-12-31", "models": "era5",
            "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum", "timezone": "Europe/Bratislava"})
        if r.status_code == 429:
            print(f"  limit Open-Meteo po {stiahnute} bunkách – pokračuje ďalší beh")
            break
        r.raise_for_status()
        j = r.json()
        d = j["daily"]
        vb = j.get("elevation") or 0
        n = len(d["time"])
        rokov = n / 365.25
        zr = sum(x or 0 for x in d["precipitation_sum"]) / rokov
        sneh = sum(1 for x in d["snowfall_sum"] if (x or 0) >= 1) / rokov
        for o in podla_bunky[b]:
            dt = GRAD * ((vysky.get(o["kod"]) or vb) - vb)
            tp = [x + dt for x in d["temperature_2m_mean"] if x is not None]
            tmax = [x + dt for x in d["temperature_2m_max"] if x is not None]
            tmin = [x + dt for x in d["temperature_2m_min"] if x is not None]
            obce[o["kod"]] = [round(sum(tp) / len(tp), 1), round(zr), round(sum(1 for x in tmin if x < 0) / rokov),
                              round(sum(1 for x in tmax if x >= 25) / rokov), round(sum(1 for x in tmax if x >= 30) / rokov, 1), round(sneh)]
        hotove.add(b)
        stiahnute += 1
        time.sleep(3)
    sr = None
    if len(hotove) == len(podla_bunky):
        sr = [median([v[i] for v in obce.values()]) for i in range(6)]
    print(f"Klíma: tento beh {stiahnute} buniek, spolu {len(hotove)}/{len(podla_bunky)}, obcí {len(obce)}" + (f", medián SR {sr}" if sr else ""))
    if stiahnute == 0 and zostava:
        raise RuntimeError("Open-Meteo: nič sa nestiahlo")
    if stiahnute or not SUBOR.exists():
        zapis_ak_zmena(SUBOR, {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "obdobie": obdobie,
                               "polia": ["priemerná teplota °C", "zrážky mm/rok", "mrazové dni", "letné dni (≥ 25 °C)", "tropické dni (≥ 30 °C)", "dni so snežením (≥ 1 cm)"],
                               "hotovo": sr is not None, "sr": sr,
                               "zdroj": {"nazov": "Open-Meteo – historické počasie (reanalýza ERA5, Copernicus/ECMWF)", "url": "https://open-meteo.com"},
                               "bunky": sorted(hotove), "obce": dict(sorted(obce.items()))}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Obce – klíma (Open-Meteo)")
