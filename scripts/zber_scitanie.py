"""Sčítanie obyvateľov, domov a bytov 2021 (SODB) – Bratislava a mestské časti.

Výstup: data/scitanie-bratislava.json

Zdroj: ŠÚ SR STATdata (statdata.statistics.sk), kocky SODB om78xx – hromadné stiahnutie CSV
(otvorené dáta, bez kľúča). Berieme rok 2021 a 17 mestských častí; mesto = ich súčet.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

VYSTUP = Path(__file__).resolve().parent.parent / "data" / "scitanie-bratislava.json"
API = "https://statdata.statistics.sk/public/api/dc"
ROK = "2021"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"

# kocka → (názov témy, stĺpec s kategóriou, ďalšie stĺpce, ktoré sčítame / filtrujeme)
KOCKY = {
    "vek": ("om7803rr", "Vekové skupiny", "e_age"),
    "ekonomicka_aktivita": ("om7803rr", "Ekonomická aktivita", "e_wstatus"),
    "vzdelanie": ("om7809rr", "Najvyššie dosiahnuté vzdelanie", "e_edu"),
    "narodnost": ("om7806rr", "Národnosť", "e_national"),
    "nabozenstvo": ("om7805rr", "Náboženské vyznanie", "e_religion"),
    "jazyk": ("om7804rr", "Materinský jazyk", "e_mtongue"),
    "rodinny_stav": ("om7808rr", "Rodinný stav", "e_marital"),
    "domacnosti": ("om7822rr", "Domácnosti podľa počtu členov", "e_poc_clen_cd"),
    "byty_vlastnictvo": ("om7819rr", "Byty podľa formy vlastníctva", "e_ownerb"),
    "byty_izby": ("om7818rr", "Byty podľa počtu obytných miestností", None),
    "byty_plocha": ("om7820rr", "Byty podľa podlahovej plochy", None),
}

s = requests.Session()
s.headers["User-Agent"] = UA
_cache: dict[str, list[dict]] = {}


def kocka(kod: str) -> list[dict]:
    if kod not in _cache:
        r = s.get(f"{API}/opendata/cube/dataset/{kod}/download", params={"type": "CSV", "lang": "SK"}, timeout=300)
        r.raise_for_status()
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        text = zf.read(zf.namelist()[0]).decode("utf-8-sig", errors="replace")
        _cache[kod] = [r for r in csv.DictReader(io.StringIO(text)) if r.get("e_year") == ROK]
    return _cache[kod]


def mc_nazov(t: str) -> str | None:
    m = re.match(r"Bratislava - mestská časť (.+)$", (t or "").strip())
    return m.group(1).strip() if m else None


def spracuj(tema: str, kod: str, kat_stlpec: str | None) -> dict:
    riadky = kocka(kod)
    if not riadky:
        raise RuntimeError(f"{kod}: žiadne riadky za {ROK}")
    stlpce = [c for c in riadky[0] if c not in ("e_nuts14", "e_nuts15", "e_year", "hodnota")]
    if kat_stlpec is None or kat_stlpec not in stlpce:
        # kategória = prvý stĺpec, ktorý nie je pohlavie ani typ domu
        kandidati = [c for c in stlpce if c not in ("e_sex", "e_buildtype")]
        kat_stlpec = kandidati[0] if kandidati else stlpce[0]
    ostatne = [c for c in stlpce if c != kat_stlpec]
    # pri ostatných stĺpcoch berieme „Spolu“, ak existuje; inak sčítame cez všetky hodnoty
    ma_spolu = {c: any(r[c].strip() == "Spolu" for r in riadky) for c in ostatne}
    data: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in riadky:
        mc = mc_nazov(r["e_nuts15"])
        if not mc:
            continue
        if any(ma_spolu[c] and r[c].strip() != "Spolu" for c in ostatne):
            continue
        kat = r[kat_stlpec].strip()
        try:
            data[mc][kat] += float(r["hodnota"] or 0)
        except ValueError:
            pass
    if len(data) < 17:
        raise RuntimeError(f"{kod}/{tema}: len {len(data)} mestských častí")
    kategorie = sorted({k for d in data.values() for k in d}, key=lambda k: -sum(d.get(k, 0) for d in data.values()))
    spolu_kat = "Spolu" if "Spolu" in kategorie else None
    mesto = {k: round(sum(d.get(k, 0) for d in data.values())) for k in kategorie}
    return {
        "kocka": kod, "stlpec": kat_stlpec, "kategorie": [k for k in kategorie if k != spolu_kat],
        "mesto": mesto, "mestske_casti": {mc: {k: round(v) for k, v in d.items()} for mc, d in sorted(data.items())},
    }


def main() -> int:
    vystup = {"rok": int(ROK), "zdroj": {"nazov": "ŠÚ SR – Sčítanie obyvateľov, domov a bytov 2021 (STATdata)", "url": "https://statdata.statistics.sk", "licencia": "CC BY 4.0"}, "temy": {}}
    chyby = []
    for tema, (kod, nazov, stlpec) in KOCKY.items():
        try:
            t = spracuj(tema, kod, stlpec)
            t["nazov"] = nazov
            vystup["temy"][tema] = t
            top = sorted(((k, v) for k, v in t["mesto"].items() if k != "Spolu"), key=lambda x: -x[1])[:5]
            print(f"OK {tema} ({kod}, {t['stlpec']}): {len(t['kategorie'])} kategórií; {top}")
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{tema}: {e}")
            print(f"CHYBA {tema}: {e}")
    if not vystup["temy"]:
        raise RuntimeError("; ".join(chyby))
    stary = json.loads(VYSTUP.read_text(encoding="utf-8")) if VYSTUP.exists() else {}
    if stary.get("temy") != vystup["temy"]:
        vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        VYSTUP.write_text(json.dumps(vystup, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("Uložené.")
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
            print(f"::error title=Zber sčítania::{type(e).__name__}: {sprava}")
        sys.exit(1)
