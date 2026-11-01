"""Štatistický úrad SR – STATdata (statdata.statistics.sk), náhrada za zrušené DATAcube API (data.statistics.sk).

DATAcube (JSON-stat s kódmi číselníkov) ŠÚ SR koncom októbra 2026 vypol – datacube.statistics.sk len presmeruje na
STATdata. Kocky majú rovnaké kódy (om7101rr, st3004rr, sp3801qr …), ale otvorené dáta sú celé tabuľky v CSV
s popismi namiesto kódov (stĺpce e_nuts14, e_nuts15, e_year, e_indic, e_unit … a „hodnota“).

  riadky("om7101rr") → [{"e_nuts14": "Okres Bratislava III", "e_nuts15": "…", "e_year": "2025", "hodnota": 36108.0}, …]

Prázdne a dôverné hodnoty („.“, „-“, „x“) sa vynechajú. Kocka sa v rámci behu stiahne len raz.
"""

from __future__ import annotations

import csv
import io
import zipfile

import requests

URL = "https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/{}/download?type=CSV&lang=SK"
WEB = "https://statdata.statistics.sk"
_s = requests.Session()
_s.headers["User-Agent"] = "mestovcislach.sk (otvorene data; github.com/karolgajdosik/mestovcislach)"
_cache: dict[str, list[dict]] = {}

# kraje → NUTS 3 kódy (výstupy webu ich používajú ako kľúče)
NUTS3 = {"Slovenská republika": "SK0", "Bratislavský kraj": "SK010", "Trnavský kraj": "SK021", "Trenčiansky kraj": "SK022",
         "Nitriansky kraj": "SK023", "Žilinský kraj": "SK031", "Banskobystrický kraj": "SK032", "Prešovský kraj": "SK041", "Košický kraj": "SK042"}


def _cislo(x: str) -> float | None:
    x = (x or "").strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None


def riadky(kocka: str) -> list[dict]:
    if kocka in _cache:
        return _cache[kocka]
    r = _s.get(URL.format(kocka), timeout=600)
    r.raise_for_status()
    if r.content[:2] != b"PK":
        raise RuntimeError(f"STATdata {kocka}: nečakaná odpoveď ({r.content[:120]!r})")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    text = z.read(z.namelist()[0]).decode("utf-8-sig", errors="replace")
    out = []
    for x in csv.DictReader(io.StringIO(text)):
        v = _cislo(x.get("hodnota", ""))
        if v is None:
            continue
        x = {k: (val or "").strip() for k, val in x.items()}
        x["hodnota"] = v
        out.append(x)
    if not out:
        raise RuntimeError(f"STATdata {kocka}: prázdna tabuľka")
    _cache[kocka] = out
    return out


def zdroj(kocka: str, nazov: str) -> dict:
    return {"nazov": f"ŠÚ SR – {nazov} ({kocka})", "url": WEB, "licencia": "CC BY 4.0"}
