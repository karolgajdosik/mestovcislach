"""Priebežné výsledky komunálnych volieb z webu Štatistického úradu (volbysr.sk/oso/json) – kým nie je hotový balík XLSX.

Počas sčítavania ŠÚ SR nezverejňuje tabuľky na stiahnutie, len JSON pre svoju stránku „Výsledky v obciach“:
  json/graph01/<kód obce>.json – súhrn: C03 % spracovaných okrskov, C04 zapísaní, C05 voliči, C06 účasť %,
                                  C09 platné lístky pre voľbu primátora, C11–C14 zvolený primátor (meno, priezvisko,
                                  strana, %) – vyplnené až keď je obec spracovaná
  json/tab05/<kód obce>.json   – kandidáti na primátora s hlasmi (priebežne len Bratislava a Košice):
                                  C02 meno, C03 priezvisko, C04 strany, C05 hlasy, C06 %
Mená kandidátov sú verejné údaje (meno, strana, hlasy).
"""

from __future__ import annotations

import requests

WEB = "https://volbysr.sk/oso/json"
KODY = {"bratislava": "582000", "trnava": "506745", "trencin": "505820", "nitra": "500011", "zilina": "517402",
        "banska-bystrica": "508438", "presov": "524140", "kosice": "599981"}
UA = {"User-Agent": "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"}


def _c(x) -> float:
    try:
        return float(str(x or "").replace("\xa0", "").replace(" ", "").replace(",", ".") or 0)
    except ValueError:
        return 0.0


def _get(cesta: str):
    r = requests.get(f"{WEB}/{cesta}", headers=UA, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def mesto(slug: str) -> dict | None:
    """Priebežný stav mesta v tvare data/mesta/<slug>.json → komunalne[rok]; None, ak ešte nie je nič spracované."""
    kod = KODY[slug]
    g = (_get(f"graph01/{kod}.json") or [None])[0]
    if not g:
        return None
    pct = _c(g.get("C03"))
    if pct <= 0 or not str(g.get("C04") or "").strip():
        return None
    platne = _c(g.get("C09"))
    kandidati = []
    for r in _get(f"tab05/{kod}.json") or []:
        hl = int(_c(r.get("C05")))
        kandidati.append({"meno": f"{(r.get('C02') or '').strip()} {(r.get('C03') or '').strip()}".strip(), "strany": (r.get("C04") or "").strip(),
                          "hlasy": hl, "podiel": round(_c(r.get("C06")), 2), "zvoleny": False})
    if not kandidati and str(g.get("C11") or "").strip():
        p = round(_c(g.get("C14")), 2)
        kandidati = [{"meno": f"{g['C11'].strip()} {str(g.get('C12') or '').strip()}".strip(), "strany": str(g.get("C13") or "").strip(),
                      "hlasy": round(platne * p / 100) if platne else 0, "podiel": p, "zvoleny": True}]
    kandidati.sort(key=lambda k: -k["hlasy"])
    hotovo = pct >= 100
    if hotovo and kandidati and not any(k["zvoleny"] for k in kandidati):
        kandidati[0]["zvoleny"] = True  # relatívna väčšina po spracovaní všetkých okrskov
    if not kandidati:
        return None
    return {
        "ucast": {"zapisani": int(_c(g.get("C04"))), "volili": int(_c(g.get("C05"))), "ucast_pct": round(_c(g.get("C06")), 2)},
        "spracovanie": {"okrsky": None, "spolu": None, "pct": round(pct, 2), "priebezne": not hotovo, "zdroj": "volbysr.sk (priebežne)"},
        "primator": kandidati,
        "zastupitelstvo": {"poslancov": 0, "mandaty": [], "poslanci": []},
    }


if __name__ == "__main__":
    for s in KODY:
        d = mesto(s)
        print(s, d and d["spracovanie"], d and [(k["meno"], k["podiel"], k["zvoleny"]) for k in d["primator"][:2]])
