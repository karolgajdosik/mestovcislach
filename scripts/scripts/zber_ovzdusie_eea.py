"""Dlhodobá kvalita ovzdušia v krajských mestách – merania staníc z Európskej environmentálnej agentúry (EEA).

Zdroj: EEA Air Quality Download Service (eeadmz1-downloads-api-appservice.azurewebsites.net) – hodinové merania
staníc SHMÚ; overené dáta (E1a) do minulých rokov a priebežné (E2a) pre posledné obdobie. Licencia: EEA (ODC-BY / CC BY 4.0).

Pre každé mesto a látku (PM10, PM2,5, NO2): ročný priemer každej stanice (len roky s ≥ 75 % platných hodín),
priemer a maximum staníc mesta; pri PM10 počet dní s denným priemerom nad 50 µg/m³ (limit EÚ: najviac 35 dní).

Výstup: data/mesta/ovzdusie.json
"""

from __future__ import annotations

import io
import json
import time
from collections import defaultdict
from datetime import date, datetime, timezone

import pyarrow.parquet as pq

from spolocne import DATA, KOREN, s, spusti, zapis_ak_zmena

API = "https://eeadmz1-downloads-api-appservice.azurewebsites.net/ParquetFile/urls"
MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))
EEA_MESTO = {"bratislava": "Bratislava", "kosice": "Kosice", "presov": "Presov", "zilina": "Zilina", "banska-bystrica": "Banská Bystrica",
             "nitra": "Nitra", "trnava": "Trnava", "trencin": "Trencín"}
LATKY = {"PM10": "PM10", "PM2.5": "PM2,5", "NO2": "NO2"}
OD = 2013


def urls(mesto: str, latka: str, dataset: int, od: str, do: str) -> list[str]:
    body = {"countries": ["SK"], "cities": [mesto], "pollutants": [latka], "dataset": dataset, "source": "Api",
            "dateTimeStart": f"{od}T00:00:00Z", "dateTimeEnd": f"{do}T00:00:00Z", "aggregationType": "hour"}
    for pokus in range(3):
        try:
            r = s.post(API, json=body, timeout=180)
            if r.status_code == 200:
                return [u.strip() for u in r.text.splitlines()[1:] if u.strip().startswith("http")]
        except Exception:  # noqa: BLE001
            pass
        time.sleep(10 * (pokus + 1))
    raise RuntimeError(f"EEA {mesto} {latka}: API nedostupné")


def stanica(url: str, latka: str) -> tuple[str, dict]:
    """(kód stanice, {rok: {"priemer", "hodin", "dni_nad_50"}})"""
    t = pq.read_table(io.BytesIO(s.get(url, timeout=300).content), columns=["Samplingpoint", "Start", "Value", "Validity"])
    body = t.column("Samplingpoint").to_pylist()
    kod = (body[0] if body else url.rsplit("/", 1)[-1]).split("/")[-1].replace("SPO-", "").split("_")[0]
    dni: dict[date, list[float]] = defaultdict(list)
    for zac, hod, plat in zip(t.column("Start").to_pylist(), t.column("Value").to_pylist(), t.column("Validity").to_pylist()):
        if hod is None or plat is None or plat <= 0 or zac.year < OD:
            continue
        dni[zac.date()].append(float(hod))
    roky: dict[int, dict] = defaultdict(lambda: {"sucet": 0.0, "hodin": 0, "nad": 0})
    for d, hodnoty in dni.items():
        r = roky[d.year]
        r["sucet"] += sum(hodnoty)
        r["hodin"] += len(hodnoty)
        if latka == "PM10" and len(hodnoty) >= 18 and sum(hodnoty) / len(hodnoty) > 50:
            r["nad"] += 1
    return kod, {str(rok): {"priemer": round(v["sucet"] / v["hodin"], 1), "hodin": v["hodin"], **({"dni_nad_50": v["nad"]} if latka == "PM10" else {})}
                 for rok, v in roky.items() if v["hodin"]}


def main() -> int:
    dnes = date.today()
    vystup: dict = {"zdroj": {"nazov": "Európska environmentálna agentúra – merania kvality ovzdušia (stanice SHMÚ)",
                              "url": "https://eeadmz1-downloads-webapp.azurewebsites.net/"},
                    "limity": {"PM10": {"eu": 40, "who": 15, "dni_eu": 35}, "PM2,5": {"eu": 25, "eu_2030": 10, "who": 5}, "NO2": {"eu": 40, "eu_2030": 20, "who": 10}},
                    "mesta": {}}
    chyby = 0
    for m in MESTA:
        latky = {}
        for latka, nazov in LATKY.items():
            try:
                stanice: dict[str, dict] = {}
                for dataset, od, do in ((2, f"{OD}-01-01", f"{dnes.year - 1}-12-31"), (1, f"{dnes.year - 1}-01-01", dnes.isoformat())):
                    for u in urls(EEA_MESTO[m["slug"]], latka, dataset, od, do):
                        kod, roky = stanica(u, latka)
                        for rok, v in roky.items():
                            # overené dáta majú prednosť pred priebežnými
                            if rok not in stanice.setdefault(kod, {}) or dataset == 2:
                                stanice[kod][rok] = v
            except Exception as e:  # noqa: BLE001
                chyby += 1
                print(f"::warning title=Ovzdušie {m['nazov']} {latka}::{e}")
                continue
            roky_mesta: dict[str, dict] = {}
            for rok in sorted({r for st in stanice.values() for r in st}):
                rocne = [st[rok] for st in stanice.values() if rok in st and st[rok]["hodin"] >= (6570 if int(rok) < dnes.year else 1)]
                if not rocne:
                    continue
                roky_mesta[rok] = {"priemer": round(sum(x["priemer"] for x in rocne) / len(rocne), 1), "max": max(x["priemer"] for x in rocne),
                                   "stanic": len(rocne), "neuplny": int(rok) >= dnes.year}
                if latka == "PM10":
                    roky_mesta[rok]["dni_nad_50"] = max(x.get("dni_nad_50", 0) for x in rocne)
            if roky_mesta:
                latky[nazov] = roky_mesta
        vystup["mesta"][m["slug"]] = latky
        print(f"{m['nazov']}: " + ", ".join(f"{k} {max(v)} {v[max(v)]['priemer']}" for k, v in latky.items()))
    if chyby > 8:
        raise RuntimeError(f"Ovzdušie EEA: {chyby} chýb")
    vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zapis_ak_zmena(DATA / "mesta" / "ovzdusie.json", vystup)
    return 0


if __name__ == "__main__":
    spusti(main, "Ovzdušie miest (EEA)")
