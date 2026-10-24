"""Bývanie: ceny nehnuteľností a bytová výstavba v Bratislave (Štatistický úrad SR, DATAcube API).

- sp3801qr – Indexy realizačných cien nehnuteľností na bývanie, regionálne, štvrťročne (HPI):
  Bratislavský kraj a SR, spolu / nové / existujúce, index k rovnakému obdobiu minulého roka
  a k predchádzajúcemu štvrťroku.
- st3004rr – Byty: začaté, dokončené, rozostavané, priemerná obytná plocha – ročne za okresy
  Bratislava I–V a Bratislavu spolu.

Výstup: data/byvanie-bratislava.json
"""

from __future__ import annotations

import re
from datetime import datetime

from spolocne import DATA, s, spusti, zapis_ak_zmena
from zber_obyvatelstvo import rozbal_jsonstat

API = "https://data.statistics.sk/api/v2/dataset"
OKRESY = {"SK0101": "Bratislava I", "SK0102": "Bratislava II", "SK0103": "Bratislava III", "SK0104": "Bratislava IV", "SK0105": "Bratislava V"}
CASTI_OKRESOV = {
    "Bratislava I": "Staré Mesto",
    "Bratislava II": "Ružinov, Vrakuňa, Podunajské Biskupice",
    "Bratislava III": "Nové Mesto, Rača, Vajnory",
    "Bratislava IV": "Karlova Ves, Dúbravka, Lamač, Devín, Devínska Nová Ves, Záhorská Bystrica",
    "Bratislava V": "Petržalka, Jarovce, Rusovce, Čunovo",
}


def kocka(cesta: str) -> list[dict]:
    r = s.get(f"{API}/{cesta}", params={"lang": "sk"}, timeout=120)
    r.raise_for_status()
    return rozbal_jsonstat(r.json())


def ceny() -> dict:
    riadky = kocka("sp3801qr/SK0,SK010/all/all/all/all")
    rad: dict[str, dict] = {}
    for r in riadky:
        obdobie = f"{r['sp3801qr_rok']}-Q{re.search(r'[1-4]', str(r['sp3801qr_stv'])).group(0)}"  # kód „1. Q.“
        kluc = f"{'ba' if r['nuts13'] == 'SK010' else 'sr'}_{r['sp3801qr_nakneh'].lower()}_{'rr' if r['sp3801qr_mj'] == 'b_romr' else 'qq'}"
        rad.setdefault(obdobie, {"obdobie": obdobie})[kluc] = round(float(r["hodnota"]), 2)
    obdobia = sorted(rad)
    # reťazový index od prvého štvrťroka (= 100) z medzištvrťročných indexov
    for k in ("ba_total", "sr_total", "ba_dw_new", "ba_dw_exst"):
        uroven = 100.0
        for i, o in enumerate(obdobia):
            q = rad[o].get(f"{k}_qq")
            if i and q:
                uroven *= q / 100
            rad[o][f"{k}_idx"] = round(uroven, 2)
    zoznam = [rad[o] for o in obdobia if "ba_total_rr" in rad[o]]
    if len(zoznam) < 8:
        raise RuntimeError(f"HPI: podozrivo málo štvrťrokov ({len(zoznam)})")
    return {"zdroj": {"nazov": "ŠÚ SR – Indexy realizačných cien nehnuteľností na bývanie, regionálne (sp3801qr)", "url": "https://datacube.statistics.sk", "licencia": "CC BY 4.0"},
            "rad": zoznam}


def vystavba() -> dict:
    riadky = kocka("st3004rr/SK0101,SK0102,SK0103,SK0104,SK0105/all/all")
    roky: dict[str, dict] = {}
    for r in riadky:
        roky.setdefault(str(r["st3004rr_rok"]), {}).setdefault(OKRESY[r["nuts14"]], {})[r["st3004rr_ukaz"]] = r["hodnota"]
    # Bratislava spolu = súčet okresov; priemerná plocha vážená počtom dokončených bytov
    for rok, okresy in roky.items():
        spolu: dict = {}
        for k in ("ROZOST_BYT_ZAC", "ZAC_BYT", "DOKONC_BYT", "ROZOST_BYT_KON"):
            hodnoty = [o[k] for o in okresy.values() if o.get(k) is not None]
            if len(hodnoty) == len(OKRESY):
                spolu[k] = sum(hodnoty)
        vahy = [(o["OBYT_PLOCH"], o.get("DOKONC_BYT") or 0) for o in okresy.values() if o.get("OBYT_PLOCH")]
        if vahy and sum(v for _, v in vahy):
            spolu["OBYT_PLOCH"] = round(sum(p * v for p, v in vahy) / sum(v for _, v in vahy), 1)
        okresy["Bratislava"] = spolu
    zoradene = [r for r in sorted(roky) if "DOKONC_BYT" in roky[r]["Bratislava"]]
    if len(zoradene) < 10:
        raise RuntimeError(f"Výstavba bytov: podozrivo málo rokov ({len(zoradene)})")
    return {"zdroj": {"nazov": "ŠÚ SR – Byty, vybrané ukazovatele (st3004rr)", "url": "https://datacube.statistics.sk", "licencia": "CC BY 4.0"},
            "okresy_casti": CASTI_OKRESOV,
            "roky": {r: roky[r] for r in zoradene}}


def main() -> int:
    data = {"aktualizovane": datetime.now().isoformat(timespec="seconds"), "ceny": ceny(), "vystavba": vystavba()}
    zapis_ak_zmena(DATA / "byvanie-bratislava.json", data)
    posledne = data["ceny"]["rad"][-1]
    rok = list(data["vystavba"]["roky"])[-1]
    print(f"Ceny: {posledne['obdobie']} BA {posledne.get('ba_total_rr')} SR {posledne.get('sr_total_rr')}; "
          f"byty {rok}: {data['vystavba']['roky'][rok]['Bratislava']}")
    return 0


if __name__ == "__main__":
    spusti(main, "Zber bývanie")
