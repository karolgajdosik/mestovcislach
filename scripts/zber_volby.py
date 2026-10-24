"""Výsledky volieb v Bratislave a jej mestských častiach (ŠÚ SR – volby.statistics.sk).

Výstup: data/volby-bratislava.json

Používa otvorené CSV súbory ŠÚ SR:
  tab02d – súhrnné výsledky (voliči, účasť) za obce
  tab03e – hlasy pre politické subjekty za obce
  tab01 / tab03a – to isté za celé Slovensko (na porovnanie)
Mestské časti Bratislavy sú v nich samostatné obce (územný obvod 101 = Bratislava).

Nové voľby sa pridajú doplnením riadku do zoznamu VOLBY.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

VYSTUP = Path(__file__).resolve().parent.parent / "data" / "volby-bratislava.json"
ZAKLAD = "https://volby.statistics.sk/opendata"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
OBVOD_BRATISLAVA = "101"

VOLBY = [
    {
        "id": "nrsr2023",
        "nazov": "Voľby do Národnej rady SR 2023",
        "kratky": "Parlament 2023",
        "datum": "2023-09-30",
        "cesta": "nrsr/2023/NRSR2023_SK",
    },
    {
        "id": "ep2024",
        "nazov": "Voľby do Európskeho parlamentu 2024",
        "kratky": "Európsky parlament 2024",
        "datum": "2024-06-08",
        "cesta": "eup/2024/EP2024_SK",
    },
]

session = requests.Session()
session.headers["User-Agent"] = UA


def nacitaj_csv(url: str) -> list[dict]:
    r = session.get(url, timeout=180)
    r.raise_for_status()
    text = r.content.decode("utf-8-sig")
    oddelovac = ";" if text.split("\n", 1)[0].count(";") > text.split("\n", 1)[0].count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=oddelovac))


def cislo(s: str) -> float:
    return float((s or "0").replace(",", ".").replace("\xa0", "").replace(" ", ""))


def stlpec(riadok: dict, *nazvy: str) -> str:
    for n in nazvy:
        if n in riadok:
            return riadok[n]
    raise KeyError(f"Chýba stĺpec {nazvy[0]!r}; stĺpce: {list(riadok)[:20]}")


def strany(riadky: list[dict]) -> list[dict]:
    vysledok: dict[str, int] = {}
    for r in riadky:
        nazov = stlpec(r, "Názov politického subjektu").strip()
        vysledok[nazov] = vysledok.get(nazov, 0) + int(cislo(stlpec(r, "Počet platných hlasov")))
    spolu = sum(vysledok.values()) or 1
    return sorted(
        ({"nazov": n, "hlasy": h, "podiel": round(100 * h / spolu, 2)} for n, h in vysledok.items()),
        key=lambda s: -s["hlasy"],
    )


def suhrn(riadky: list[dict]) -> dict:
    zapisani = sum(int(cislo(stlpec(r, "Počet zapísaných voličov"))) for r in riadky)
    zucastneni = sum(int(cislo(stlpec(r, "Počet zúčastnených voličov"))) for r in riadky)
    return {
        "zapisani": zapisani,
        "zucastneni": zucastneni,
        "ucast": round(100 * zucastneni / zapisani, 2) if zapisani else None,
    }


def spracuj(v: dict) -> dict:
    url = f"{ZAKLAD}/{v['cesta']}"
    ucast = [r for r in nacitaj_csv(f"{url}_tab02d.csv") if stlpec(r, "Kód územného obvodu") == OBVOD_BRATISLAVA]
    hlasy = [r for r in nacitaj_csv(f"{url}_tab03e.csv") if stlpec(r, "Kód územného obvodu") == OBVOD_BRATISLAVA]
    if len(ucast) != 17:
        raise RuntimeError(f"{v['id']}: čakal som 17 mestských častí, našiel som {len(ucast)}.")

    casti = []
    for u in ucast:
        kod = stlpec(u, "Kód obce")
        nazov = stlpec(u, "Názov obce").replace("Bratislava - ", "").strip()
        s = strany([h for h in hlasy if stlpec(h, "Kód obce") == kod])
        casti.append({"kod_obce": kod, "nazov": nazov, **suhrn([u]), "strany": [x for x in s if x["hlasy"] > 0]})
    casti.sort(key=lambda c: c["nazov"])

    # Celé Slovensko na porovnanie.
    sr_ucast = nacitaj_csv(f"{url}_tab01.csv")[0]
    sr_strany = strany(nacitaj_csv(f"{url}_tab03a.csv"))
    sr = {
        "zapisani": int(cislo(stlpec(sr_ucast, "Počet zapísaných voličov"))),
        "zucastneni": int(cislo(stlpec(sr_ucast, "Počet zúčastnených voličov"))),
        "ucast": cislo(stlpec(sr_ucast, "Účasť voličov v %")),
        "strany": sr_strany,
    }
    return {
        "id": v["id"],
        "nazov": v["nazov"],
        "kratky": v["kratky"],
        "datum": v["datum"],
        "zdroj": f"{url}_tab03e.csv",
        "mesto": {**suhrn(ucast), "strany": strany(hlasy)},
        "slovensko": sr,
        "mestske_casti": casti,
    }


def main() -> int:
    # Výsledky ukončených volieb sa nemenia: ak je zdroj nedostupný (archív volby.statistics.sk od 10/2026 vracia 404),
    # ponecháme uložené a skončíme len s upozornením, aby denná chyba nezakrývala skutočné problémy.
    stare = {x["id"]: x for x in json.loads(VYSTUP.read_text(encoding="utf-8")).get("volby", [])} if VYSTUP.exists() else {}
    vysledky = []
    for v in VOLBY:
        try:
            vysledky.append(spracuj(v))
        except Exception as e:  # noqa: BLE001
            if v["id"] not in stare:
                raise
            print(f"::warning title=Voľby {v['id']}::zdroj nedostupný ({type(e).__name__}: {str(e)[:150]}), ponechávam uložené výsledky")
            vysledky.append(stare[v["id"]])
    novy = {
        "zdroj": {"nazov": "Štatistický úrad SR – výsledky volieb", "url": "https://volby.statistics.sk"},
        "volby": vysledky,
    }
    if VYSTUP.exists():
        stary = json.loads(VYSTUP.read_text(encoding="utf-8"))
        if stary.get("volby") == vysledky:
            print("Bez zmeny – voľby sú aktuálne.")
            return 0
    novy["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    VYSTUP.write_text(json.dumps(novy, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for v in vysledky:
        vitaz = v["mesto"]["strany"][0]
        print(f"OK {v['id']}: účasť BA {v['mesto']['ucast']} % (SR {v['slovensko']['ucast']} %), "
              f"víťaz BA {vitaz['nazov']} {vitaz['podiel']} %")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber volieb::{type(e).__name__}: {sprava}")
        sys.exit(1)
