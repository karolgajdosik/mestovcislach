"""Spoločné pomôcky pre zbery: hranice mestských častí, register adries MV SR, chyby v Actions.

Register adries (Ministerstvo vnútra SR, data.slovensko.sk) – GeoJSON pre každú mestskú časť,
aktualizovaný denne: ulica, súpisné a orientačné číslo, súradnice. Slúži na geokódovanie
(pamiatky, spádové obvody škôl).
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable

import requests
from shapely.geometry import Point, shape
from shapely.prepared import prep

KOREN = Path(__file__).resolve().parent.parent
DATA = KOREN / "data"
VEREJNE = KOREN / "public" / "data"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"

s = requests.Session()
s.headers["User-Agent"] = UA

# LAU2 kódy mestských častí v registri adries (data.slovensko.sk, „Adresy v obci Bratislava-…“)
LAU_ADRESY = {
    "Staré Mesto": "SK0101528595", "Podunajské Biskupice": "SK0102529311", "Ružinov": "SK0102529320",
    "Vrakuňa": "SK0102529338", "Nové Mesto": "SK0103529346", "Rača": "SK0103529354", "Vajnory": "SK0103529362",
    "Devínska Nová Ves": "SK0104529371", "Dúbravka": "SK0104529389", "Karlova Ves": "SK0104529397",
    "Devín": "SK0104529401", "Lamač": "SK0104529419", "Záhorská Bystrica": "SK0104529427",
    "Čunovo": "SK0105529435", "Jarovce": "SK0105529443", "Petržalka": "SK0105529460", "Rusovce": "SK0105529494",
}
URL_ADRESY = "https://rageo.minv.sk/opendata/dataset/address_by_lau2_{}.geojson"


def bez_diakritiky(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def norm_ulica(t: str) -> str:
    t = bez_diakritiky(t).lower()
    t = re.sub(r"\bnam(\.|estie)\s*", "namestie ", t)
    t = re.sub(r"\bul\.?\s*$|\bulica\b", "", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def norm_mc(t: str) -> str | None:
    """„Bratislava 1-Staré Mesto“, „Bratislava - mestská časť Petržalka“, „Bratislava-Ružinov“ → názov MČ."""
    t = (t or "").strip()
    for mc in LAU_ADRESY:
        if t.endswith(mc) or bez_diakritiky(t).lower().endswith(bez_diakritiky(mc).lower()):
            return mc
    skratky = {"P.Biskupice": "Podunajské Biskupice", "Dev.Nová Ves": "Devínska Nová Ves", "Záhor.Bystrica": "Záhorská Bystrica",
               "Záh. Bystrica": "Záhorská Bystrica", "Pod. Biskupice": "Podunajské Biskupice"}
    for k, v in skratky.items():
        if t.endswith(k):
            return v
    return None


def hranice():
    """[(kod_obce, nazov, shapely geometria)] 17 mestských častí."""
    gj = json.loads((DATA / "hranice-bratislava.geojson").read_text(encoding="utf-8"))
    # v hraniciach je preklep „Podunajské Biskupce“
    return [(f["properties"]["kod_obce"], f["properties"]["nazov"].replace("Biskupce", "Biskupice"), shape(f["geometry"])) for f in gj["features"]]


def mc_podla_polohy() -> Callable[[float, float], str | None]:
    casti = [(nazov, prep(g)) for _, nazov, g in hranice()]

    def najdi(lon: float, lat: float) -> str | None:
        p = Point(lon, lat)
        for nazov, g in casti:
            if g.contains(p):
                return nazov
        return None
    return najdi


def adresy_mv() -> list[dict]:
    """Všetky adresné body Bratislavy z registra adries: {mc, ulica, sup, ori, lon, lat}."""
    vysledok = []
    for mc, lau in LAU_ADRESY.items():
        r = s.get(URL_ADRESY.format(lau), timeout=300)
        r.raise_for_status()
        for f in r.json()["features"]:
            p, g = f["properties"], f.get("geometry")
            if not g or g.get("type") != "Point":
                continue
            lon, lat = g["coordinates"][:2]
            vysledok.append({"mc": mc, "ulica": (p.get("streetname") or "").strip(), "sup": str(p.get("propertyregistrationnumber") or "").strip(),
                             "ori": str(p.get("orientationnumber") or "").strip(), "lon": lon, "lat": lat})
    if len(vysledok) < 50000:
        raise RuntimeError(f"Register adries: podozrivo málo bodov ({len(vysledok)})")
    return vysledok


def spusti(main: Callable[[], int], nazov: str) -> None:
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title={nazov}::{type(e).__name__}: {sprava}")
        sys.exit(1)


def zapis_ak_zmena(cesta: Path, data: dict, kompaktne: bool = False, ignoruj=("aktualizovane",)) -> bool:
    """Zapíše JSON len pri zmene obsahu (okrem poľa aktualizovane). Vráti True, ak zapísal."""
    stare = json.loads(cesta.read_text(encoding="utf-8")) if cesta.exists() else {}
    nove = json.loads(json.dumps(data, ensure_ascii=False))
    if {k: v for k, v in stare.items() if k not in ignoruj} == {k: v for k, v in nove.items() if k not in ignoruj}:
        return False
    cesta.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) if kompaktne else json.dumps(data, ensure_ascii=False, indent=1)
    cesta.write_text(text + "\n", encoding="utf-8")
    return True
