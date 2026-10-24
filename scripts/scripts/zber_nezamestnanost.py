"""Miera evidovanej nezamestnanosti a počet uchádzačov o zamestnanie – okresy Bratislava I–V, kraj a Slovensko.

Zdroje:
  ŠÚ SR STATdata, kocka pr3108rr – ročná miera evidovanej nezamestnanosti k 31. 12. (okresy do 2022, kraj a SR ďalej), CSV.
  ÚPSVaR – mesačné štatistiky: aktuálny mesiac z otvorených údajov (JSON), staršie mesiace z XLSX (tabuľka 1).
  Na úrovni okresov ÚPSVaR zverejňuje podiel disponibilných uchádzačov v produktívnom veku na obyvateľstve v produktívnom veku (PDU).
Výstup: data/nezamestnanost-bratislava.json (mesačné údaje sa kumulujú)
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from datetime import date, datetime, timezone

import openpyxl

from spolocne import DATA, s, spusti, zapis_ak_zmena

URL = "https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/pr3108rr/download?type=CSV&lang=SK"
UZEMIA = ["Okres Bratislava I", "Okres Bratislava II", "Okres Bratislava III", "Okres Bratislava IV", "Okres Bratislava V", "Bratislavský kraj", "Slovenská republika"]
# okres → mestské časti (pre asistenta a stránku)
MC = {"Okres Bratislava I": "Staré Mesto", "Okres Bratislava II": "Ružinov, Vrakuňa, Podunajské Biskupice",
      "Okres Bratislava III": "Nové Mesto, Rača, Vajnory", "Okres Bratislava IV": "Karlova Ves, Dúbravka, Lamač, Devín, Devínska Nová Ves, Záhorská Bystrica",
      "Okres Bratislava V": "Petržalka, Jarovce, Rusovce, Čunovo"}


UPSVR_JSON = "https://www.upsvr.gov.sk/statistiky/open-data/UoZ-01-zakladne-ukazovatele.json"
UPSVR_XLSX = "https://www.upsvr.gov.sk/buxus/docs/statistic/mesacne/{r}/UoZaVPM_MS_{rr}{mm}.xlsx"
OKRESY = ["Bratislava I", "Bratislava II", "Bratislava III", "Bratislava IV", "Bratislava V", "Bratislavský kraj", "Slovenská republika"]
OD_MESIACA = "2023-01"


def cislo(x) -> float | None:
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def mesiac_z_xlsx(rok: int, mes: int) -> dict | None:
    r = s.get(UPSVR_XLSX.format(r=rok, rr=str(rok)[2:], mm=f"{mes:02d}"), timeout=120)
    if r.status_code != 200 or r.content[:2] != b"PK":
        return None
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    vysl = {}
    for row in wb["Tab1"].iter_rows(values_only=True):
        hodnoty = [c for c in row if c is not None]
        if not hodnoty or not isinstance(hodnoty[0], str):
            continue
        uz = {"Slovensko": "Slovenská republika"}.get(hodnoty[0].strip(), hodnoty[0].strip())
        if uz in OKRESY and len(hodnoty) >= 8:
            vysl[uz] = {"uoz": cislo(hodnoty[3]), "disp": cislo(hodnoty[-3]), "pdu": cislo(hodnoty[-1])}
    return vysl or None


def mesiac_z_json() -> tuple[str, dict] | None:
    j = s.get(UPSVR_JSON, timeout=120).json()["posts"]
    obdobie = j["description"]["period"][:7]
    vysl = {}
    for x in j["data"]:
        uz = x["uzemie"].strip()
        if uz in OKRESY:
            vysl[uz] = {"uoz": cislo(x["stav_uoz_spolu"]), "disp": cislo(x["disponibilny_pocet"]), "pdu": cislo(x["podiel_dispuoz_vpv_naopv"])}
    return (obdobie, vysl) if vysl else None


def mesacne(stare: dict) -> dict:
    data = dict(stare)
    try:
        akt = mesiac_z_json()
        if akt:
            data[akt[0]] = akt[1]
            print("ÚPSVaR JSON:", akt[0], akt[1].get("Bratislava I"))
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=ÚPSVaR JSON::{e}")
    rok, mes = int(OD_MESIACA[:4]), int(OD_MESIACA[5:])
    dnes = date.today()
    while (rok, mes) < (dnes.year, dnes.month):
        k = f"{rok}-{mes:02d}"
        if k not in data or len(data[k]) < 6:
            try:
                m = mesiac_z_xlsx(rok, mes)
                if m:
                    data[k] = {**data.get(k, {}), **m}
                    print("ÚPSVaR XLSX:", k, m.get("Bratislava I"))
            except Exception as e:  # noqa: BLE001
                print(f"::warning title=ÚPSVaR XLSX::{k}: {e}")
        mes += 1
        if mes > 12:
            rok, mes = rok + 1, 1
    return dict(sorted(data.items()))


def main() -> int:
    r = s.get(URL, timeout=180)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    text = z.read(z.namelist()[0]).decode("utf-8-sig")
    data: dict = defaultdict(lambda: defaultdict(dict))
    ukazovatele = set()
    for riadok in csv.DictReader(io.StringIO(text)):
        uz = riadok["e_nuts14"].strip()
        if uz not in UZEMIA or riadok["e_sex"].strip() in ("Muži", "Ženy"):
            continue
        ind = riadok["e_indic"].strip()
        ukazovatele.add(ind)
        try:
            data[ind][uz][riadok["e_year"].strip()] = float(riadok["hodnota"])
        except ValueError:
            continue
    print("Ukazovatele:", sorted(ukazovatele))
    miera = data.get("Miera evidovanej nezamestnanosti")
    if not miera or len(miera) < 5:
        raise RuntimeError(f"Chýba miera nezamestnanosti (ukazovatele {sorted(ukazovatele)})")
    roky = sorted({y for v in miera.values() for y in v})
    vystup = {
        "zdroj": {"nazov": "ŠÚ SR – Miera evidovanej nezamestnanosti (pr3108rr), údaje úradov práce k 31. 12.", "url": "https://statdata.statistics.sk", "licencia": "CC BY 4.0"},
        "roky": roky, "okresy_mc": MC,
        "ukazovatele": {ind: {uz: dict(sorted(v.items())) for uz, v in sorted(hodnoty.items(), key=lambda x: UZEMIA.index(x[0]))} for ind, hodnoty in sorted(data.items())},
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    posl = roky[-1]
    print(f"Miera {posl}:", {uz: miera.get(uz, {}).get(posl) for uz in UZEMIA})
    stare = json.loads((DATA / "nezamestnanost-bratislava.json").read_text(encoding="utf-8")).get("mesacne", {}) if (DATA / "nezamestnanost-bratislava.json").exists() else {}
    vystup["mesacne"] = mesacne(stare)
    vystup["zdroj_mesacne"] = {"nazov": "ÚPSVaR – mesačné štatistiky nezamestnanosti (podiel disponibilných uchádzačov o zamestnanie, PDU)",
                               "url": "https://www.upsvr.gov.sk/statistiky/nezamestnanost-mesacne-statistiky.html?page_id=1254"}
    zapis_ak_zmena(DATA / "nezamestnanost-bratislava.json", vystup)
    return 0


if __name__ == "__main__":
    spusti(main, "Zber nezamestnanosti")
