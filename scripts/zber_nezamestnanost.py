"""Miera evidovanej nezamestnanosti a počet uchádzačov o zamestnanie – okresy Bratislava I–V, kraj a Slovensko.

Zdroj: ŠÚ SR STATdata, kocka pr3108rr (ročné údaje z evidencie úradov práce, k 31. 12.), CSV.
Výstup: data/nezamestnanost-bratislava.json
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena

URL = "https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/pr3108rr/download?type=CSV&lang=SK"
UZEMIA = ["Okres Bratislava I", "Okres Bratislava II", "Okres Bratislava III", "Okres Bratislava IV", "Okres Bratislava V", "Bratislavský kraj", "Slovenská republika"]
# okres → mestské časti (pre asistenta a stránku)
MC = {"Okres Bratislava I": "Staré Mesto", "Okres Bratislava II": "Ružinov, Vrakuňa, Podunajské Biskupice",
      "Okres Bratislava III": "Nové Mesto, Rača, Vajnory", "Okres Bratislava IV": "Karlova Ves, Dúbravka, Lamač, Devín, Devínska Nová Ves, Záhorská Bystrica",
      "Okres Bratislava V": "Petržalka, Jarovce, Rusovce, Čunovo"}


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
    zapis_ak_zmena(DATA / "nezamestnanost-bratislava.json", vystup)
    return 0


if __name__ == "__main__":
    spusti(main, "Zber nezamestnanosti")
