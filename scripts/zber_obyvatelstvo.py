"""Zber počtu obyvateľov Bratislavy a jej mestských častí z DATAcube (ŠÚ SR).

Výstup: data/obyvatelstvo-bratislava.json

Skript si sám zistí štruktúru tabuľky (dimenzie) cez API, takže nie je
potrebné ručne zadávať kódy obcí. Ak niečo nesedí, skončí chybou a
existujúci súbor s dátami neprepíše.

Spustenie:  python scripts/zber_obyvatelstvo.py
Iná tabuľka: DATACUBE_TABULKA=om7101rr python scripts/zber_obyvatelstvo.py

Pozn.: ŠÚ SR presúva dáta z DATAcube do novej databázy STATdata
(DATAcube sa po 15. 9. 2026 už neaktualizuje). Keď bude k dispozícii
obec-level tabuľka v STATdata, stačí vymeniť funkcie stiahni_*.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://data.statistics.sk/api/v2"
TABULKA = os.environ.get("DATACUBE_TABULKA", "om7101rr")
VYSTUP = Path(__file__).resolve().parent.parent / "data" / "obyvatelstvo-bratislava.json"

# Popisy prvkov, ktoré znamenajú "spolu" (napr. obe pohlavia spolu).
SPOLU = {"spolu", "celkom", "úhrn", "uhrn", "total", "spolu (muži a ženy)"}
SPOLU_KODY = {"_T", "T", "SPOLU", "0"}

session = requests.Session()
session.headers["User-Agent"] = "mestovcislach.sk (otvorene data; github.com/karolgajdosik/mestovcislach)"


def ziskaj_json(url: str) -> dict:
    r = session.get(url, params={"lang": "sk"}, timeout=60)
    r.raise_for_status()
    return r.json()


def kategorie(obj: dict) -> list[tuple[str, str]]:
    """Vráti zoznam (kód, popis) z JSON-stat dimenzie v poradí podľa indexu."""
    cat = obj.get("category")
    if cat is None:
        # Niektoré odpovede majú dimenziu zabalenú ešte o úroveň nižšie.
        for v in obj.values():
            if isinstance(v, dict) and "category" in v:
                cat = v["category"]
                break
    if cat is None:
        raise ValueError("Odpoveď neobsahuje 'category' – neznámy formát dimenzie.")
    index = cat.get("index")
    labels = cat.get("label", {})
    if isinstance(index, dict):
        kody = sorted(index, key=index.get)
    elif isinstance(index, list):
        kody = index
    else:
        kody = list(labels)
    return [(k, str(labels.get(k, k))) for k in kody]


def stiahni_dimenzie(tabulka: str) -> list[tuple[str, list[tuple[str, str]]]]:
    dims = []
    for n in range(1, 10):
        dim_id = f"{tabulka}_dim{n}"
        try:
            data = ziskaj_json(f"{API}/dimension/{tabulka}/{dim_id}")
        except requests.HTTPError:
            break
        try:
            dims.append((dim_id, kategorie(data)))
        except ValueError:
            break
    if not dims:
        raise RuntimeError(f"Tabuľka {tabulka}: nepodarilo sa načítať dimenzie.")
    return dims


def je_obec_bratislava(popis: str) -> bool:
    p = popis.strip()
    return "Bratislava" in p and not p.lower().startswith("okres")


def vyber_kody(dims):
    """Pre každú dimenziu vyberie, ktoré prvky chceme."""
    vyber, typ = [], {}
    for dim_id, prvky in dims:
        popisy = [p for _, p in prvky]
        if any(je_obec_bratislava(p) for p in popisy) and len(prvky) > 50:
            kody = [k for k, p in prvky if je_obec_bratislava(p)]
            typ["uzemie"] = dim_id
        elif all(re.fullmatch(r"\d{4}", p.strip()) for p in popisy):
            kody = ["all"]
            typ["rok"] = dim_id
        elif len(prvky) == 1:
            kody = [prvky[0][0]]
        else:
            spolu = [k for k, p in prvky if p.strip().lower() in SPOLU or k in SPOLU_KODY]
            if not spolu:
                zoznam = ", ".join(f"{k}={p}" for k, p in prvky[:15])
                raise RuntimeError(
                    f"Dimenzia {dim_id}: nenašiel som prvok 'spolu'. Prvky: {zoznam}"
                )
            kody = [spolu[0]]
        vyber.append(kody)
    if "uzemie" not in typ or "rok" not in typ:
        raise RuntimeError(f"Nenašiel som dimenziu územia alebo roku: {typ}")
    return vyber, typ


def rozbal_jsonstat(ds: dict) -> list[dict]:
    """JSON-stat 2.0 dataset -> zoznam riadkov {dim_id: kód, ..., 'hodnota': x}."""
    if "dimension" not in ds and len(ds) == 1:
        ds = next(iter(ds.values()))  # JSON-stat 1.x obal
    ids = ds.get("id") or ds["dimension"]["id"]
    size = ds.get("size") or ds["dimension"]["size"]
    kody = []
    for d in ids:
        kody.append([k for k, _ in kategorie(ds["dimension"][d])])
    hodnoty = ds["value"]
    pocet = 1
    for s in size:
        pocet *= s
    riadky = []
    for i in range(pocet):
        v = hodnoty.get(str(i)) if isinstance(hodnoty, dict) else hodnoty[i]
        if v is None:
            continue
        zvysok, riadok = i, {}
        for d, s, k in reversed(list(zip(ids, size, kody))):
            riadok[d] = k[zvysok % s]
            zvysok //= s
        riadok["hodnota"] = v
        riadky.append(riadok)
    return riadky


def main() -> int:
    dims = stiahni_dimenzie(TABULKA)
    vyber, typ = vyber_kody(dims)
    nazvy = dict(next(p for d, p in dims if d == typ["uzemie"]))

    url = f"{API}/dataset/{TABULKA}/" + "/".join(",".join(k) for k in vyber)
    data = ziskaj_json(url)
    riadky = rozbal_jsonstat(data)
    if not riadky:
        raise RuntimeError("API vrátilo prázdne dáta.")

    uzemia: dict[str, dict] = {}
    for r in riadky:
        kod = r[typ["uzemie"]]
        rok = r[typ["rok"]]
        u = uzemia.setdefault(kod, {"kod": kod, "nazov": nazvy.get(kod, kod), "roky": {}})
        u["roky"][rok] = int(round(float(r["hodnota"])))

    for u in uzemia.values():
        u["roky"] = dict(sorted(u["roky"].items()))
        u["nazov_kratky"] = re.sub(r"^Bratislava\s*[-–]\s*(mestská časť\s*)?", "", u["nazov"]).strip()

    # Mesto ako celok má názov presne "Bratislava"; ostatné sú mestské časti.
    mesto = next((u for u in uzemia.values() if u["nazov"].strip() == "Bratislava"), None)
    casti = sorted((u for u in uzemia.values() if u is not mesto), key=lambda u: u["nazov_kratky"])
    if mesto is None:
        # Tabuľka neobsahuje mesto ako celok -> súčet mestských častí.
        roky: dict[str, int] = {}
        for u in casti:
            for rok, v in u["roky"].items():
                roky[rok] = roky.get(rok, 0) + v
        mesto = {"kod": "SUCET", "nazov": "Bratislava", "nazov_kratky": "Bratislava",
                 "roky": dict(sorted(roky.items())), "poznamka": "súčet mestských častí"}

    vystup = {
        "zdroj": {
            "nazov": "Štatistický úrad SR – DATAcube",
            "tabulka": TABULKA,
            "url": url,
        },
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mesto": mesto,
        "mestske_casti": casti,
    }
    # Ak sa dáta nezmenili, súbor neprepisujeme (žiadny zbytočný commit).
    if VYSTUP.exists():
        stare = json.loads(VYSTUP.read_text(encoding="utf-8"))
        if stare.get("mesto") == mesto and stare.get("mestske_casti") == casti:
            print("Bez zmeny – dáta sú aktuálne.")
            return 0
    VYSTUP.parent.mkdir(parents=True, exist_ok=True)
    VYSTUP.write_text(json.dumps(vystup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    posledny = max(mesto["roky"])
    pocet = f"{mesto['roky'][posledny]:,}".replace(",", " ")
    print(f"OK: {mesto['nazov']} + {len(casti)} mestských častí, rok {posledny}: {pocet} obyvateľov")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        sys.exit(1)
