"""Sčítače dopravy v Bratislave – kedy je na cestách najviac áut, bicyklov a chodcov.

Výstup: data/scitace-bratislava.json

Zdroj: data.bratislava.sk – tri datasety s hodinovými počtami zo sčítačov mesta
(autá, cyklisti, chodci; ArcGIS služby s rovnakou štruktúrou polí).
Autá meria len niekoľko sčítačov (Vajanského nábrežie, Dunajská), väčšina
sčítačov je na cyklotrasách – sčítače bez dát v danej kategórii vynechávame.

Počítame za posledných 8 týždňov (v miestnom čase Europe/Bratislava):
  - priemerný hodinový profil pre pracovný deň a víkend (oba smery),
  - rannú a večernú špičku, priemerný počet za pracovný deň,
  - posledný celý deň s dátami.
Dni, keď sčítač v danom smere nameral 0 (výpadok), vynechávame. Smer, ktorý
sčítač prakticky nemeria (< 5 % prejazdov), neuvádzame.
Navyše mesačný priemer za deň za celé obdobie (agregácia na serveri).
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

VYSTUP = Path(__file__).resolve().parent.parent / "data" / "scitace-bratislava.json"
KATEGORIE = {
    "auta": "7b5628f9234a461e8becfa37665290b3",
    "cyklisti": "097b7c8bc4b94560a7e34c9e64139a5e",
    "chodci": "84ba9f28423e4a52aae97c8cfb7d58e6",
}
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
TZ = ZoneInfo("Europe/Bratislava")
TYZDNE = 8

s = requests.Session()
s.headers["User-Agent"] = UA


def sluzba(item: str) -> tuple[str, dict]:
    it = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{item}", params={"f": "json"}, timeout=60).json()
    url = it["url"].rstrip("/")
    url = url if url[-1].isdigit() else url + "/0"
    zdroj = {"nazov": it.get("title"), "url": f"https://data.bratislava.sk/datasets/{item}", "licencia": "CC BY 4.0"}
    return url, zdroj


def stiahni(url: str, od: str) -> list[dict]:
    riadky, offset = [], 0
    while True:
        r = s.get(url + "/query", params={
            "where": f"DATUM_A_CAS >= '{od}'", "outFields": "NAZOV,ZEMEPISNA_SIRKA,ZEMEPISNA_DLZKA,SMER_DO,SMER_Z,DATUM_A_CAS,POCET_DO,POCET_Z",
            "returnGeometry": "false", "orderByFields": "ObjectId", "resultOffset": offset, "resultRecordCount": 1000, "f": "json",
        }, timeout=120).json()
        if "error" in r:
            raise RuntimeError(f"{url}: {r['error']}")
        davka = [f["attributes"] for f in r.get("features", [])]
        riadky += davka
        if len(davka) < 1000 and not r.get("exceededTransferLimit"):
            return riadky
        offset += len(davka)


def mesacne(url: str) -> dict[str, dict[str, int]]:
    """Priemerný počet za deň po mesiacoch pre každý sčítač (agregácia na serveri). Pri chybe vráti {}."""
    try:
        stat = [{"statisticType": "sum", "onStatisticField": "POCET_DO", "outStatisticFieldName": "do_"},
                {"statisticType": "sum", "onStatisticField": "POCET_Z", "outStatisticFieldName": "z_"},
                {"statisticType": "count", "onStatisticField": "ObjectId", "outStatisticFieldName": "n"}]
        # Hodiny s nulou v oboch smeroch sú výpadky – nerátame ich do priemeru.
        r = s.get(url + "/query", params={
            "where": "POCET_DO > 0 OR POCET_Z > 0", "outStatistics": json.dumps(stat),
            "groupByFieldsForStatistics": "NAZOV, SUBSTRING(DATUM_A_CAS, 1, 7)", "f": "json",
        }, timeout=180).json()
        if "error" in r:
            print(f"Mesačná agregácia nedostupná: {r['error'].get('message')}")
            return {}
        vysledok: dict[str, dict[str, int]] = defaultdict(dict)
        for f in r.get("features", []):
            a = f["attributes"]
            mesiac = next((v for k, v in a.items() if isinstance(v, str) and len(v) == 7 and v[4] == "-"), None)
            hodin = a.get("n") or 0
            if mesiac and hodin >= 24 * 15:  # aspoň ~15 dní dát v mesiaci
                vysledok[a["NAZOV"].strip()][mesiac] = round(((a.get("do_") or 0) + (a.get("z_") or 0)) / (hodin / 24))
        return {k: dict(sorted(v.items())) for k, v in vysledok.items()}
    except Exception as e:  # noqa: BLE001
        print(f"Mesačná agregácia zlyhala: {e}")
        return {}


def smer(text: str | None) -> str:
    """Upratanie popisu smeru (napr. 'Cyklomost Slobody Pedestrians IN - na Slovensko' -> 'na Slovensko')."""
    t = re.sub(r"^.*\b(IN|OUT)\s*-\s*", "", (text or "").strip())
    return "opačný smer" if t.upper().startswith("NIE JE") else t


def spracuj(data: list[dict], trend: dict) -> tuple[list[dict], list[str]]:
    # sčítač -> smer -> deň -> hodina -> počet
    hodnoty: dict[str, dict[str, dict[str, dict[int, float]]]] = defaultdict(lambda: {"do": defaultdict(dict), "z": defaultdict(dict)})
    info: dict[str, dict] = {}
    for r in data:
        t = datetime.fromisoformat(r["DATUM_A_CAS"]).astimezone(TZ)
        den, hod = t.date().isoformat(), t.hour
        n = r["NAZOV"].strip()
        info.setdefault(n, {"nazov": n.split(" - ", 1)[-1].strip(), "id": n.split(" - ")[0].strip("# "),
                            "lat": r["ZEMEPISNA_SIRKA"], "lon": r["ZEMEPISNA_DLZKA"],
                            "smer_do": smer(r.get("SMER_DO")), "smer_z": smer(r.get("SMER_Z"))})
        hodnoty[n]["do"][den][hod] = r.get("POCET_DO") or 0
        hodnoty[n]["z"][den][hod] = r.get("POCET_Z") or 0

    vcera = (datetime.now(TZ) - timedelta(days=1)).date().isoformat()
    scitace = []
    for n, smery in hodnoty.items():
        celkom = {sm: sum(sum(h.values()) for h in smery[sm].values()) for sm in ("do", "z")}
        if sum(celkom.values()) == 0:
            continue  # sčítač v tejto kategórii nemeria
        aktivne = [sm for sm in ("do", "z") if celkom[sm] >= 0.05 * sum(celkom.values())]
        profily: dict[str, list] = {}
        posledny_den = None
        for smer in aktivne:
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
        if all(v is None for k, p in profily.items() if k.startswith("pracovny") for v in p):
            continue  # bez platných dát v sledovanom období

        def spicka(od_h: int, do_h: int) -> dict:
            najlepsie = None
            for smer in aktivne:
                for h in range(od_h, do_h):
                    v = profily[f"pracovny_{smer}"][h]
                    if v is not None and (najlepsie is None or v > najlepsie["pocet"]):
                        najlepsie = {"hodina": h, "smer": info[n][f"smer_{smer}"], "pocet": v}
            return najlepsie or {}

        denne = sum(v for k, p in profily.items() if k.startswith("pracovny") for v in p if v is not None)
        posledny = None
        if posledny_den:
            posledny = {"datum": posledny_den}
            for smer in aktivne:
                posledny[smer] = [smery[smer][posledny_den].get(h) for h in range(24)]
            posledny["spolu"] = sum(v or 0 for smer in aktivne for v in posledny[smer])
        zaznam = {**info[n], "smery": aktivne, **profily, "pracovny_den_spolu": denne,
                  "spicka_rano": spicka(5, 11), "spicka_vecer": spicka(14, 20),
                  "posledny_den": posledny, "mesacne": trend.get(n, {})}
        for smer in ("do", "z"):
            if smer not in aktivne:
                zaznam.pop(f"smer_{smer}")
        scitace.append(zaznam)
    scitace.sort(key=lambda x: -x["pracovny_den_spolu"])
    datumy = sorted({d for sm in hodnoty.values() for d in sm["do"]})
    return scitace, datumy


def main() -> int:
    od = (datetime.now(timezone.utc) - timedelta(weeks=TYZDNE)).strftime("%Y-%m-%d")
    stary = json.loads(VYSTUP.read_text(encoding="utf-8")) if VYSTUP.exists() else {}
    vystup = {"obdobie": None, "kategorie": {}}
    chyby, vsetky_datumy = [], set()
    for kat, item in KATEGORIE.items():
        try:
            url, zdroj = sluzba(item)
            data = stiahni(url, od)
            scitace, datumy = spracuj(data, mesacne(url))
            if not scitace:
                raise RuntimeError(f"žiadny sčítač s dátami ({len(data)} záznamov)")
            vystup["kategorie"][kat] = {"zdroj": zdroj, "scitace": scitace}
            vsetky_datumy.update(datumy)
            print(f"OK {kat}: {len(scitace)} sčítačov")
            for x in scitace[:4]:
                print(f"  {x['nazov']}: {x['pracovny_den_spolu']}/pracovný deň, ráno {x['spicka_rano']}, večer {x['spicka_vecer']}, trend {len(x['mesacne'])} mes.")
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{kat}: {e}")
            if kat in stary.get("kategorie", {}):
                vystup["kategorie"][kat] = stary["kategorie"][kat]  # ponecháme staré dáta
    if not vystup["kategorie"]:
        raise RuntimeError("; ".join(chyby))
    d = sorted(vsetky_datumy) or [stary.get("obdobie", {}).get("od"), stary.get("obdobie", {}).get("do")]
    vystup["obdobie"] = {"od": d[0], "do": d[-1], "tyzdne": TYZDNE}

    if stary.get("obdobie") == vystup["obdobie"] and stary.get("kategorie") == vystup["kategorie"]:
        print("Sčítače: bez zmeny")
    else:
        vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        VYSTUP.write_text(json.dumps(vystup, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"Uložené: {vystup['obdobie']}")
    if chyby:
        raise RuntimeError("; ".join(chyby))
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
