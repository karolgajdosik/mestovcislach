"""Klimatický atlas Bratislavy (citlivosť a riziká), dostupnosť kúpalísk a hustota obyvateľov – mriežky.

Zdroj: data.bratislava.sk – Atlas hodnotenia zraniteľnosti a rizík nepriaznivých dôsledkov zmeny klímy
(štvorce 200 × 200 m), Dostupnosť kúpalísk, Demografia podľa miesta sčítania (raster 1 × 1 km).
Licencia CC BY 4.0.

Každú bunku ukladáme kompaktne ako obdĺžnik [juh, západ, sever, východ, hodnota] (WGS84).

Výstupy: public/data/klima/<vrstva>.json, data/klima-bratislava.json (zoznam vrstiev a štatistiky)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from statistics import quantiles

from pyproj import Transformer

from spolocne import DATA, VEREJNE, s, spusti, url_vrstvy, zapis_ak_zmena

VRSTVY = {  # kľúč: (prefix ID, názov, pole s hodnotou, popis)
    "riziko_horucavy": ("575142ec", "Riziko horúčav pre obyvateľov", "hodnota", "kombinácia horúčav, citlivosti obyvateľov (vek, hustota) a schopnosti prispôsobiť sa"),
    "citlivost_horucavy": ("8eedf533", "Citlivosť obyvateľov na horúčavy", "hodnota", "podiel citlivých skupín obyvateľov (deti, seniori) a hustota"),
    "riziko_celkove": ("be617c15", "Riziko zmeny klímy – celkové", "priemer", "priemer rizík horúčav, zrážok pre budovy a dopravnú infraštruktúru"),
    "citlivost_celkova": ("367d0139", "Citlivosť na zmenu klímy – celková", "priemer", "priemer citlivosti na horúčavy, zrážky a dopravnú infraštruktúru"),
    "riziko_zrazky_budovy": ("61a9db38", "Riziko prívalových zrážok pre budovy", "hodnota", "ohrozenie budov intenzívnymi zrážkami"),
    "citlivost_zrazky_budovy": ("7a8c8bd7", "Citlivosť budov na zrážky", "hodnota", "zraniteľnosť budov pri prívalových dažďoch"),
    "riziko_doprava": ("074fc4b3", "Riziko zrážok pre dopravnú infraštruktúru", "hodnota", "ohrozenie ciest a koľají zrážkami"),
    "kupaliska": ("7e67f27f", "Dostupnosť kúpalísk", "kupanie_n", "normalizovaná dostupnosť kúpalísk a kúpania (vyššie = lepšia)"),
}
HUSTOTA = "ffe51d79"
_3035 = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)


def plne_id(prefix: str) -> str:
    for p in json.loads((DATA / "katalog-bratislava.json").read_text(encoding="utf-8"))["datasety"]:
        if p["id"].startswith(prefix):
            return p["id"]
    raise RuntimeError(f"{prefix} nie je v inventári")


def stiahni(url: str, polia: str, geometria: bool) -> list[dict]:
    vysl, offset = [], 0
    while True:
        r = s.get(url + "/query", params={"where": "1=1", "outFields": polia, "returnGeometry": str(geometria).lower(), "outSR": 4326,
                                          "geometryPrecision": 5, "resultOffset": offset, "resultRecordCount": 2000, "f": "json"}, timeout=240).json()
        if "error" in r:
            raise RuntimeError(r["error"])
        f = r.get("features", [])
        vysl += f
        if len(f) < 2000 and not r.get("exceededTransferLimit"):
            return vysl
        offset += len(f)


def main() -> int:
    (VEREJNE / "klima").mkdir(parents=True, exist_ok=True)
    prehlad, chyby = {}, []
    for kluc, (prefix, nazov, pole, popis) in VRSTVY.items():
        try:
            data = stiahni(url_vrstvy(plne_id(prefix)), pole, True)
            bunky = []
            for f in data:
                v = f["attributes"].get(pole)
                ring = (f.get("geometry") or {}).get("rings", [[]])[0]
                if v is None or not ring:
                    continue
                xs, ys = [p[0] for p in ring], [p[1] for p in ring]
                bunky.append([round(min(ys), 5), round(min(xs), 5), round(max(ys), 5), round(max(xs), 5), round(float(v), 3)])
            hodnoty = sorted(b[4] for b in bunky)
            if len(hodnoty) < 100:
                raise RuntimeError(f"len {len(hodnoty)} buniek")
            hranice = [round(q, 3) for q in quantiles(hodnoty, n=5)]
            zapis_ak_zmena(VEREJNE / "klima" / f"{kluc}.json", {"nazov": nazov, "popis": popis, "hranice": hranice, "min": hodnoty[0], "max": hodnoty[-1],
                                                                "bunky": bunky}, kompaktne=True)
            prehlad[kluc] = {"nazov": nazov, "popis": popis, "buniek": len(bunky), "min": hodnoty[0], "max": hodnoty[-1], "hranice": hranice,
                             "zdroj": f"https://data.bratislava.sk/datasets/{plne_id(prefix)}"}
            print(f"{kluc}: {len(bunky)} buniek, hodnoty {hodnoty[0]}–{hodnoty[-1]}, kvintily {hranice}")
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{kluc}: {e}")
            print(f"CHYBA {kluc}: {e}")

    # Hustota obyvateľov – raster 1 km (kód bunky INSPIRE, napr. 1kmN2765E4790 alebo CRS3035RES1000mN2765000E4790000)
    try:
        data = stiahni(url_vrstvy(plne_id(HUSTOTA)), "*", False)
        a = [f["attributes"] for f in data]
        print("Hustota ukážka:", {k: a[0][k] for k in list(a[0])[:8]})
        kod_pole = next(k for k in a[0] if k.lower().startswith("grid"))
        pocet_pole = next(k for k in a[0] if re.match(r"počet_obyvateľov$", k, re.I))
        najnovsie: dict[str, dict] = {}
        rok_pole = next((k for k in a[0] if re.search(r"^rok|obdobie|dátum", k, re.I)), None)
        for r in a:
            k = str(r.get(kod_pole))
            if rok_pole and k in najnovsie and str(najnovsie[k].get(rok_pole)) > str(r.get(rok_pole)):
                continue
            najnovsie[k] = r
        bunky = []
        for k, r in najnovsie.items():
            m = re.search(r"N(\d+)E(\d+)", k)
            if not m or not r.get(pocet_pole):
                continue
            n, e = int(m.group(1)), int(m.group(2))
            if n < 100000:
                n, e = n * 1000, e * 1000
            lon1, lat1 = _3035.transform(e, n)
            lon2, lat2 = _3035.transform(e + 1000, n + 1000)
            bunky.append([round(lat1, 5), round(lon1, 5), round(lat2, 5), round(lon2, 5), int(float(r[pocet_pole]))])
        if len(bunky) < 50:
            raise RuntimeError(f"len {len(bunky)} buniek s kódom")
        hodnoty = sorted(b[4] for b in bunky)
        hranice = [round(q) for q in quantiles(hodnoty, n=5)]
        zapis_ak_zmena(VEREJNE / "klima" / "hustota.json", {"nazov": "Obyvatelia na km² (sčítanie 2021)", "popis": "počet obyvateľov v štvorci 1 × 1 km",
                                                           "hranice": hranice, "min": hodnoty[0], "max": hodnoty[-1], "bunky": bunky}, kompaktne=True)
        prehlad["hustota"] = {"nazov": "Hustota obyvateľov (1 km²)", "buniek": len(bunky), "min": hodnoty[0], "max": hodnoty[-1], "hranice": hranice,
                              "zdroj": f"https://data.bratislava.sk/datasets/{plne_id(HUSTOTA)}"}
        print(f"hustota: {len(bunky)} buniek, max {hodnoty[-1]}")
    except Exception as e:  # noqa: BLE001
        chyby.append(f"hustota: {e}")
        print(f"CHYBA hustota: {e}")
    if len(prehlad) < 4:
        raise RuntimeError("; ".join(chyby))
    zapis_ak_zmena(DATA / "klima-bratislava.json", {"vrstvy": prehlad, "chyby": chyby, "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return 0


if __name__ == "__main__":
    spusti(main, "Zber klimatického atlasu")
