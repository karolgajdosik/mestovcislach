"""Priebežné výsledky komunálnych volieb z webu Štatistického úradu (volbysr.sk/oso/json) – kým nie je hotový balík XLSX.

Počas sčítavania ŠÚ SR nezverejňuje tabuľky na stiahnutie, len JSON pre svoju stránku „Výsledky v obciach“:
  json/graph01/<kód obce>.json – súhrn: C03 % spracovaných okrskov, C04 zapísaní, C05 voliči, C06 účasť %,
                                  C09 platné lístky pre voľbu primátora/starostu, C11 zvolený (celé meno), C12 strany,
                                  C13 hlasy, C14 % – vyplnené až keď je obec spracovaná; C15 počet poslancov
  json/tab05/<kód obce>.json   – kandidáti na primátora/starostu s hlasmi (počas noci len Bratislava a Košice):
                                  C02 meno, C03 priezvisko, C04 strany, C05 hlasy, C06 %, C07 „zvolený“
Poslanci (tab06/tab07) sú len v konečných výsledkoch – tie prídu v balíku XLSX.
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


def obec(kod: str) -> dict | None:
    """Voľba primátora/starostu v obci (mestskej časti): účasť, kandidáti, % spracovaných okrskov."""
    g = (_get(f"graph01/{kod}.json") or [None])[0]
    if not g:
        return None
    pct = _c(g.get("C03"))
    if pct <= 0 or not str(g.get("C04") or "").strip():
        return None
    kandidati = []
    for r in _get(f"tab05/{kod}.json") or []:
        kandidati.append({"meno": f"{(r.get('C02') or '').strip()} {(r.get('C03') or '').strip()}".strip(), "strany": (r.get("C04") or "").strip(),
                          "hlasy": int(_c(r.get("C05"))), "podiel": round(_c(r.get("C06")), 2),
                          "zvoleny": str(r.get("C07") or "").strip().lower().startswith("zvolen")})
    if not kandidati and str(g.get("C11") or "").strip():
        kandidati = [{"meno": str(g["C11"]).strip(), "strany": str(g.get("C12") or "").strip(), "hlasy": int(_c(g.get("C13"))),
                      "podiel": round(_c(g.get("C14")), 2), "zvoleny": True}]
    kandidati.sort(key=lambda k: -k["hlasy"])
    if pct >= 100 and kandidati and not any(k["zvoleny"] for k in kandidati):
        kandidati[0]["zvoleny"] = True  # relatívna väčšina po spracovaní všetkých okrskov
    return {"nazov": str(g.get("C01") or "").strip(), "pct": round(pct, 2), "kandidati": kandidati,
            "ucast": {"zapisani": int(_c(g.get("C04"))), "volili": int(_c(g.get("C05"))), "ucast_pct": round(_c(g.get("C06")), 2)}}


def mesto(slug: str) -> dict | None:
    """Priebežný stav mesta v tvare data/mesta/<slug>.json → komunalne[rok]; None, ak ešte nie je nič spracované."""
    o = obec(KODY[slug])
    if not o or not o["kandidati"]:
        return None
    return {
        "ucast": o["ucast"],
        "spracovanie": {"okrsky": None, "spolu": None, "pct": o["pct"], "priebezne": o["pct"] < 100, "zdroj": "volbysr.sk (priebežne)"},
        "primator": o["kandidati"],
        "zastupitelstvo": {"poslancov": 0, "mandaty": [], "poslanci": []},
    }


# mestské časti Bratislavy (kódy obcí ŠÚ SR)
MC_BA = ["528595", "529311", "529320", "529338", "529346", "529354", "529362", "529371", "529389", "529397", "529401",
         "529419", "529427", "529435", "529443", "529460", "529494"]


def starostovia_ba() -> list[dict]:
    out = []
    for kod in MC_BA:
        o = obec(kod)
        if not o or not o["kandidati"]:
            continue
        out.append({"kod": kod, "nazov": o["nazov"].replace("Bratislava - ", "").strip(), "ucast": o["ucast"], "kandidati": o["kandidati"],
                    "miestne_zastupitelstvo": {"poslancov": 0, "mandaty": []}})
    return sorted(out, key=lambda s: s["nazov"])


if __name__ == "__main__":
    print("starostovia BA:", [(s["nazov"], s["kandidati"][0]["meno"]) for s in starostovia_ba()][:5])
    for s in KODY:
        d = mesto(s)
        print(s, d and d["spracovanie"], d and [(k["meno"], k["podiel"], k["zvoleny"]) for k in d["primator"][:2]])
