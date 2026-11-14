"""Kvalita ovzdušia – ročné priemery z najbližšej stanice SHMÚ (cez EEA Air Quality Download Service) → data/obce/ovzdusie.json.

  stanice: metadáta EEA (PanEuropean_metadata.csv, Countrycode SK) – súradnice vzorkovacích miest
  hodnoty: parquet súbory pre každé vzorkovacie miesto (dataset 2 = overené E1a; ak posledný rok chýba, dataset 1 = aktuálne UTD),
           PM10 (5), PM2,5 (6001), NO2 (8); ročný priemer z platných hodinových/denných hodnôt (Validity ≥ 1) pri pokrytí ≥ 75 %
  obec: najbližšia stanica do 15 km od stredu obce (pre každú látku zvlášť), uloží sa aj vzdialenosť a názov stanice.

Limity EÚ (ročný priemer): PM10 40 µg/m³, PM2,5 25 µg/m³ (od 2030 20 a 10), NO2 40 µg/m³; odporúčanie WHO 2021: 15, 5 a 10 µg/m³.
"""

from __future__ import annotations

import csv
import io
import math
from collections import defaultdict
from datetime import date, datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE

API = "https://eeadmz1-downloads-api-appservice.azurewebsites.net/ParquetFile/urls"
META = "https://discomap.eea.europa.eu/map/fme/metadata/PanEuropean_metadata.csv"
LATKY = {5: "pm10", 6001: "pm25", 8: "no2"}
MAX_KM = 15


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    dy = (a[0] - b[0]) * 111.2
    dx = (a[1] - b[1]) * 111.2 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def stanice() -> dict[str, dict]:
    """vzorkovacie miesto (SK/SPO-…) -> {lat, lon, nazov, typ}"""
    r = s.get(META, timeout=300)
    r.raise_for_status()
    out = {}
    for x in csv.DictReader(io.StringIO(r.content.decode("utf-8", "replace")), delimiter="\t"):
        if x.get("Countrycode") != "SK":
            continue
        try:
            lat, lon = float(x["Latitude"]), float(x["Longitude"])
        except (KeyError, ValueError):
            continue
        sp = x.get("SamplingPoint", "").strip().split("/")[-1]
        nazov = (x.get("AirQualityStationNatCode") or x.get("AirQualityStation") or "").strip()
        out[sp] = {"lat": lat, "lon": lon, "stanica": x.get("AirQualityStation", "").strip(), "nazov": nazov,
                   "typ": (x.get("AirQualityStationType") or "").strip(), "oblast": (x.get("AirQualityStationArea") or "").strip()}
    return out


def priemery(rok: int) -> dict[tuple[str, int], float]:
    """(vzorkovacie miesto, látka) -> ročný priemer µg/m³"""
    import pyarrow.parquet as pq
    out = {}
    for ds in (2, 1):
        for kod in LATKY:
            if any(k[1] == kod for k in out) and ds == 1:
                continue  # overené dáta sú – aktuálne netreba
            r = s.post(API, json={"countries": ["SK"], "cities": [], "pollutants": [{5: "PM10", 6001: "PM2.5", 8: "NO2"}[kod]], "dataset": ds, "source": "Api"}, timeout=120)
            r.raise_for_status()
            urls = [u.strip() for u in r.content.decode("utf-8-sig").splitlines()[1:] if u.strip().startswith("http")]
            for u in urls:
                try:
                    t = pq.read_table(io.BytesIO(s.get(u, timeout=120).content), columns=["Samplingpoint", "Pollutant", "Start", "End", "Value", "Validity"]).to_pydict()
                except Exception:  # noqa: BLE001
                    continue
                suma = n = 0.0
                hod = 0.0
                for st, en, v, val in zip(t["Start"], t["End"], t["Value"], t["Validity"]):
                    if st.year != rok or v is None or val is None or val < 1:
                        continue
                    h = (en - st).total_seconds() / 3600
                    suma += float(v) * h
                    hod += h
                    n += 1
                if hod >= 0.75 * 8760 and t["Samplingpoint"]:
                    out[(t["Samplingpoint"][0].split("/")[-1], kod)] = round(suma / hod, 1)
    return out


def main() -> int:
    rok = date.today().year - 1
    st = stanice()
    pr = priemery(rok)
    if len(pr) < 20:  # overené dáta za minulý rok ešte nemusia byť – skúsiť predminulý
        rok -= 1
        pr = priemery(rok)
    body: dict[int, list] = defaultdict(list)
    for (sp, kod), v in pr.items():
        if sp in st:
            body[kod].append((st[sp], v))
    obce = {}
    for o in OBCE:
        if not o.get("poloha"):
            continue
        z = {}
        for kod, kl in LATKY.items():
            kand = [(km(tuple(o["poloha"]), (x["lat"], x["lon"])), x, v) for x, v in body[kod]]
            if not kand:
                continue
            d, x, v = min(kand, key=lambda t: t[0])
            if d <= MAX_KM:
                z[kl] = [v, round(d, 1), x["nazov"], x["typ"]]
        if z:
            obce[o["kod"]] = z
    print(f"Ovzdušie {rok}: stanice {len(st)} miest, priemerov {len(pr)} ({dict((LATKY[k], len(v)) for k, v in body.items())}), obcí do {MAX_KM} km: {len(obce)}")
    if len(obce) < 200:
        raise RuntimeError(f"ovzdušie: len {len(obce)} obcí")
    zapis_ak_zmena(DATA / "obce" / "ovzdusie.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rok": rok, "max_km": MAX_KM,
        "polia": ["ročný priemer µg/m³", "vzdialenosť km", "stanica", "typ stanice"],
        "zdroj": {"nazov": "SHMÚ – meranie kvality ovzdušia, údaje cez EEA Air Quality Download Service", "url": "https://eeadmz1-downloads-webapp.azurewebsites.net/"},
        "obce": dict(sorted(obce.items()))}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Obce – kvalita ovzdušia (SHMÚ/EEA)")
