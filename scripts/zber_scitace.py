"""Dopravné sčítače v Bratislave – kedy sú zápchy.

Výstup: data/scitace-bratislava.json

Zdroj: data.bratislava.sk – „Počet prejazdov vozidiel podľa sčítačov za hodinu“
(ArcGIS služba vozidla_00, 19 sčítačov, hodinové počty v oboch smeroch od 8/2022).

Počítame za posledných 8 týždňov (v miestnom čase Europe/Bratislava):
  - priemerný hodinový profil pre pracovný deň a víkend (oba smery),
  - rannú a večernú špičku, priemerný počet áut za pracovný deň,
  - posledný celý deň s dátami.
Dni, keď sčítač v danom smere nameral 0 áut (výpadok), vynechávame.
Navyše mesačný priemer áut za deň za celé obdobie (ak to služba dovolí agregovať).
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

VYSTUP = Path(__file__).resolve().parent.parent / "data" / "scitace-bratislava.json"
ITEM = "7b5628f9234a461e8becfa37665290b3"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
TZ = ZoneInfo("Europe/Bratislava")
TYZDNE = 8

s = requests.Session()
s.headers["User-Agent"] = UA


def sluzba() -> tuple[str, dict]:
    it = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{ITEM}", params={"f": "json"}, timeout=60).json()
    url = it["url"].rstrip("/")
    url = url if url[-1].isdigit() else url + "/0"
    zdroj = {"nazov": it.get("title"), "url": f"https://data.bratislava.sk/datasets/{ITEM}", "licencia": "CC BY 4.0"}
    return url, zdroj


def stiahni(url: str, od: str) -> list[dict]:
    riadky, offset = [], 0
    while True:
        r = s.get(url + "/query", params={
            "where": f"DATUM_A_CAS >= '{od}'", "outFields": "NAZOV,ZEMEPISNA_SIRKA,ZEMEPISNA_DLZKA,SMER_DO,SMER_Z,DATUM_A_CAS,POCET_DO,POCET_Z",
            "returnGeometry": "false", "orderByFields": "ObjectId", "resultOffset": offset, "resultRecordCount": 1000, "f": "json",
        }, timeout=120).json()
        if "error" in r:
            raise RuntimeError(f"Sčítače: {r['error']}")
        davka = [f["attributes"] for f in r.get("features", [])]
        riadky += davka
        if len(davka) < 1000 and not r.get("exceededTransferLimit"):
            return riadky
        offset += len(davka)


def mesacne(url: str) -> dict[str, dict[str, float]]:
    """Súčet áut po mesiacoch pre každý sčítač (agregácia na serveri). Pri chybe vráti {}."""
    try:
        stat = [{"statisticType": "sum", "onStatisticField": "POCET_DO", "outStatisticFieldName": "do_"},
                {"statisticType": "sum", "onStatisticField": "POCET_Z", "outStatisticFieldName": "z_"},
                {"statisticType": "count", "onStatisticField": "ObjectId", "outStatisticFieldName": "n"}]
        r = s.get(url + "/query", params={
            "where": "1=1", "outStatistics": json.dumps(stat),
            "groupByFieldsForStatistics": "NAZOV, SUBSTRING(DATUM_A_CAS, 1, 7)", "f": "json",
        }, timeout=180).json()
        if "error" in r:
            print(f"Mesačná agregácia nedostupná: {r['error'].get('message')}")
            return {}
        vysledok: dict[str, dict[str, float]] = defaultdict(dict)
        for f in r.get("features", []):
            a = f["attributes"]
            mesiac = next((v for k, v in a.items() if isinstance(v, str) and len(v) == 7 and v[4] == "-"), None)
            hodin = a.get("n") or 0
            if mesiac and hodin >= 24 * 20:  # aspoň ~20 dní dát v mesiaci
                vysledok[a["NAZOV"]][mesiac] = round(((a.get("do_") or 0) + (a.get("z_") or 0)) / (hodin / 24))
        return {k: dict(sorted(v.items())) for k, v in vysledok.items()}
    except Exception as e:  # noqa: BLE001
        print(f"Mesačná agregácia zlyhala: {e}")
        return {}


def main() -> int:
    url, zdroj = sluzba()
    od = (datetime.now(timezone.utc) - timedelta(weeks=TYZDNE)).strftime("%Y-%m-%d")
    data = stiahni(url, od)
    if len(data) < 1000:
        raise RuntimeError(f"Sčítače: podozrivo málo záznamov ({len(data)}).")

    # sčítač -> smer -> deň -> hodina -> počet
    hodnoty: dict[str, dict[str, dict[str, dict[int, float]]]] = defaultdict(lambda: {"do": defaultdict(dict), "z": defaultdict(dict)})
    info: dict[str, dict] = {}
    for r in data:
        t = datetime.fromisoformat(r["DATUM_A_CAS"]).astimezone(TZ)
        den, hod = t.date().isoformat(), t.hour
        n = r["NAZOV"].strip()
        info.setdefault(n, {"nazov": n, "lat": r["ZEMEPISNA_SIRKA"], "lon": r["ZEMEPISNA_DLZKA"],
                            "smer_do": (r.get("SMER_DO") or "").strip(), "smer_z": (r.get("SMER_Z") or "").strip()})
        hodnoty[n]["do"][den][hod] = r.get("POCET_DO") or 0
        hodnoty[n]["z"][den][hod] = r.get("POCET_Z") or 0

    vcera = (datetime.now(TZ) - timedelta(days=1)).date().isoformat()
    trend = mesacne(url)
    scitace = []
    for n, smery in hodnoty.items():
        profily = {}
        posledny_den = None
        for smer in ("do", "z"):
            pd: dict[int, list[float]] = defaultdict(list)
            vk: dict[int, list[float]] = defaultdict(list)
            for den, hodiny in smery[smer].items():
                if len(hodiny) < 20 or sum(hodiny.values()) == 0:
                    continue  # neúplný deň alebo výpadok sčítača
                cielovy = pd if datetime.fromisoformat(den).weekday() < 5 else vk
                for h, v in hodiny.items():
                    cielovy[h].append(v)
                if den <= vcera and (posledny_den is None or den > posledny_den):
                    posledny_den = den
            profily[f"pracovny_{smer}"] = [round(sum(pd[h]) / len(pd[h])) if pd[h] else None for h in range(24)]
            profily[f"vikend_{smer}"] = [round(sum(vk[h]) / len(vk[h])) if vk[h] else None for h in range(24)]
        if all(v is None for v in profily["pracovny_do"]) and all(v is None for v in profily["pracovny_z"]):
            continue  # sčítač bez platných dát v sledovanom období

        def spicka(od_h: int, do_h: int) -> dict:
            najlepsie = None
            for smer in ("do", "z"):
                for h in range(od_h, do_h):
                    v = profily[f"pracovny_{smer}"][h]
                    if v is not None and (najlepsie is None or v > najlepsie["pocet"]):
                        najlepsie = {"hodina": h, "smer": info[n][f"smer_{smer}"], "pocet": v}
            return najlepsie or {}

        denne = sum(v for smer in ("do", "z") for v in profily[f"pracovny_{smer}"] if v is not None)
        posledny = None
        if posledny_den:
            posledny = {"datum": posledny_den,
                        "do": [smery["do"][posledny_den].get(h) for h in range(24)],
                        "z": [smery["z"][posledny_den].get(h) for h in range(24)]}
            posledny["spolu"] = sum(v or 0 for v in posledny["do"] + posledny["z"])
        scitace.append({**info[n], "id": n.split(" - ")[0].strip("# "), **profily,
                        "pracovny_den_spolu": denne, "spicka_rano": spicka(5, 11), "spicka_vecer": spicka(14, 20),
                        "posledny_den": posledny, "mesacne": trend.get(n, {})})
    if len(scitace) < 5:
        raise RuntimeError(f"Sčítače: málo sčítačov s dátami ({len(scitace)}).")
    scitace.sort(key=lambda x: -x["pracovny_den_spolu"])

    datumy = sorted({d for sm in hodnoty.values() for d in sm["do"]})
    vystup = {"zdroj": zdroj, "obdobie": {"od": datumy[0], "do": datumy[-1], "tyzdne": TYZDNE}, "scitace": scitace}
    if VYSTUP.exists():
        stary = json.loads(VYSTUP.read_text(encoding="utf-8"))
        if stary.get("obdobie") == vystup["obdobie"] and stary.get("scitace") == scitace:
            print("Sčítače: bez zmeny")
            return 0
    vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    VYSTUP.write_text(json.dumps(vystup, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"OK sčítače: {len(scitace)} sčítačov, {vystup['obdobie']}, mesačný trend pre {len(trend)}")
    for x in scitace[:5]:
        print(f"  {x['nazov']}: {x['pracovny_den_spolu']} áut/pracovný deň, ranná špička {x['spicka_rano']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber sčítačov::{type(e).__name__}: {sprava}")
        sys.exit(1)
