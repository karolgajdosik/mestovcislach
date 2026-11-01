"""Školy, doprava, bezpečnosť, životné prostredie a kultúra krajských miest – Štatistický úrad SR (STATdata; do 10/2026 DATAcube).

Kocky:
  sv5001rr–sv5003rr  materské, základné školy a gymnáziá podľa obcí (počet škôl, žiakov, učiteľov) – vývoj od 1996
  Digitálna mapa škôl MŠVVaM (mapaskol.iedu.sk) – aktuálny stav po školách: typ, žiaci, pedagógovia (aj stredné školy)
  do3701rr, zp3701rr, ku3701rr, st3701rr, sv3701rr  – „… – mestá“ (európsky Urban Audit): autá, obete nehôd,
                     cyklistická sieť, cena lístka MHD, voda, odpad, kultúra, ceny bytov, predškolské zariadenia
  sk3002rr, sk3003rr majetkové a všetky trestné činy podľa krajov (polícia SR) – mesto samotné sa nesleduje;
                     STATdata už nemá členenie podľa druhu, staršie druhy z DATAcube ostávajú uložené
  om7002rr           obyvatelia krajov (na prepočet kriminality na 1 000 obyvateľov; v DATAcube om7102rr)
Staršie roky z DATAcube (napr. školy od 1996) sa zachovajú, STATdata ich dopĺňa a prepisuje.

Výstup: data/mesta/temy.json  {skoly, mestske, kriminalita}
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, KOREN, spusti, zapis_ak_zmena
import statdata as sd
from zber_mesta import norm, patri

MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))
# kocka SOŠ (sv5004rr) má posunuté popisy hodnôt (napr. „učitelia“ = počet žiakov) – stredné školy berieme z mapy škôl
SKOLY = {"ms": "sv5001rr", "zs": "sv5002rr", "gym": "sv5003rr"}
UA = ["do3701rr", "zp3701rr", "ku3701rr", "st3701rr", "sv3701rr"]


def oblasti_mesta(nazvy: list[str], mesto: str) -> list[str]:
    """Celé mesto, ak je v kocke; inak mestské časti (nikdy oboje)."""
    if mesto in {norm(n) for n in nazvy}:
        return [n for n in nazvy if norm(n) == mesto][:1]
    return [n for n in nazvy if patri(norm(n), mesto) and norm(n) != mesto and not norm(n).startswith("Okres")]


# súhrnná kategória zriaďovateľov v kockách škôl
SKOLY_SPOLU = {"ms": "Školy", "zs": "Školy (1. - 9. roč.)", "gym": "Gymnáziá"}
UKAZ_SKOLY = {"Spolu": "skol", "Počet detí": "ziakov", "Počet žiakov": "ziakov", "Počet učiteľov": "ucitelov", "Počet tried": "tried"}


def skoly() -> dict:
    vysl: dict = {m["slug"]: {} for m in MESTA}
    for druh, kocka in SKOLY.items():
        rows = sd.riadky(kocka)
        typ = next(c for c in rows[0] if c.startswith("e_educat"))
        nazvy = list(dict.fromkeys(r["e_nuts15"] for r in rows))
        for m in MESTA:
            oblasti = set(oblasti_mesta(nazvy, m["nazov"]))
            if not oblasti:
                continue
            # súhrn za všetkých zriaďovateľov; kde súhrnný riadok chýba (učitelia, triedy), sčítame štátne, súkromné a cirkevné
            spolu: dict[str, dict] = defaultdict(lambda: defaultdict(float))
            casti: dict[str, dict] = defaultdict(lambda: defaultdict(float))
            for r in rows:
                k = UKAZ_SKOLY.get(r["e_indic"])
                if not k or r["e_nuts15"] not in oblasti or "1. - 4." in r[typ]:
                    continue
                (spolu if r[typ] == SKOLY_SPOLU[druh] else casti)[r["e_year"]][k] += r["hodnota"]
            roky: dict[str, dict] = defaultdict(dict)
            for rok in set(spolu) | set(casti):
                for k in ("skol", "ziakov", "ucitelov", "tried"):
                    v = spolu[rok].get(k) or casti[rok].get(k)
                    if v:
                        roky[rok][k] = v
            vysl[m["slug"]][druh] = {rok: {k: round(v) for k, v in x.items()} for rok, x in sorted(roky.items()) if x.get("skol") or x.get("ziakov")}
        print(f"Školy {druh}: " + ", ".join(f"{s} {max(v.get(druh) or {'-': 0})}" for s, v in vysl.items()))
    return vysl


def skoly_mapa() -> dict:
    from zber_skoly_iedu import URL_MAPA, citaj, num, typ
    riadky = citaj(URL_MAPA)
    if len(riadky) < 5000:
        raise RuntimeError(f"Mapa škôl: málo riadkov ({len(riadky)})")
    vysl: dict = {}
    for m in MESTA:
        typy: dict[str, dict] = defaultdict(lambda: {"pocet": 0, "ziaci": 0, "ped": 0.0})
        stredne = []
        for x in riadky:
            obec = re.sub(r"^\d{3}\s?\d{2}\s+", "", (x.get("Obec") or "").strip())
            if not patri(obec, m["nazov"]):
                continue
            t_ = typ(x["Názov"])
            if not t_ or t_ == "ine":
                continue
            if t_ == "ss":
                t_ = "gym" if re.search(r"gym", x["Názov"], re.I) else "sos"
            ziaci, ped = num(x["Počet žiakov"]) or 0, num(x["Počet ped.zam."]) or 0
            typy[t_]["pocet"] += 1
            typy[t_]["ziaci"] += int(ziaci)
            typy[t_]["ped"] += ped
            if t_ in ("gym", "sos") and ziaci:
                stredne.append({"nazov": re.sub(r"\s+", " ", x["Názov"]).strip(), "typ": t_, "ziaci": int(ziaci), "ped": round(ped, 1),
                                "web": (x.get("Web stránka") or "").strip()})
        vysl[m["slug"]] = {"typy": {k: {**v, "ped": round(v["ped"])} for k, v in typy.items()}, "stredne": sorted(stredne, key=lambda s_: -s_["ziaci"])}
    print("Mapa škôl: " + ", ".join(f"{k} {sum(t['pocet'] for t in v['typy'].values())}" for k, v in vysl.items()))
    return vysl


# Urban Audit: (ukazovateľ, jednotka) → kľúč a popis zhodný s pôvodnými údajmi z DATAcube (web ich hľadá podľa popisu)
JEDNOTKY_ZP = {"m3": "m3", "m3 / osoba": "m3 na osobu", "medziročný index / ROMR = 100": "romr = 100", "EUR": "Euro", "kg / osoba": "kg na osobu", "tony": "t"}
PREMENUJ_KU = {"Počet subjektov profesionálneho scénického umenia": "Subjekty profesionálneho scénického umenia",
               "Návštevnosť múzeí za rok": "Návštevníci múzeí za rok"}


def ua_kluc(kocka: str, ukaz: str, jednotka: str) -> tuple[str, str] | None:
    u = re.sub(r"\s+", " ", ukaz).strip()
    if kocka == "zp3701rr":
        j = JEDNOTKY_ZP.get(jednotka, jednotka)
        return f"{u} | {j}", f"{u} – {j}"
    if kocka == "ku3701rr":
        u = PREMENUJ_KU.get(u, u)
    elif kocka in ("st3701rr", "sv3701rr"):
        if "index" in jednotka:
            u = f"{u}, index romr = 100"
        elif jednotka == "EUR":
            u = f"{u} v eurách"
        elif jednotka == "EUR / m2":
            u = f"{u} za m2"
    return u, u


def mestske(stare: dict | None = None) -> dict:
    """Urban Audit – každý ukazovateľ ako {popis: {rok: hodnota}} pre každé mesto (staršie roky z minulého behu ostávajú)."""
    stare = stare or {}
    popisy: dict = dict(stare.get("popisy") or {})
    vysl: dict = {m["slug"]: {k: dict(v) for k, v in ((stare.get("mesta") or {}).get(m["slug"]) or {}).items()} for m in MESTA}
    for kocka in UA:
        n = 0
        for r in sd.riadky(kocka):
            m = next((x for x in MESTA if x["nazov"] == norm(r["e_city"])), None)
            if not m or r.get("e_sex", "Spolu") != "Spolu":
                continue
            kj = ua_kluc(kocka, r["e_indic"], r.get("e_unit", ""))
            if not kj:
                continue
            kluc = f"{kocka}:{kj[0]}"
            popisy[kluc] = kj[1]
            vysl[m["slug"]].setdefault(kluc, {})[r["e_year"]] = r["hodnota"]
            n += 1
        print(f"{kocka}: {n} hodnôt")
    return {"popisy": popisy, "mesta": vysl}


def kriminalita(stare: dict | None = None) -> dict:
    """Trestné činy krajov (STATdata už len súhrny: sk3003rr všetky, sk3002rr majetkové) a obyvatelia krajov (om7002rr)."""
    stare = stare or {}
    kraje = sorted({m["kraj"] for m in MESTA})
    vysl: dict = {"kraje": {k: {d: dict(v) for d, v in (stare.get("kraje") or {}).get(k, {}).items()} for k in kraje},
                  "obyvatelia": {k: dict((stare.get("obyvatelia") or {}).get(k, {})) for k in kraje}}
    for kocka, druh in (("sk3003rr", "Trestné činy spolu"), ("sk3002rr", "Majetkové trestné činy spolu")):
        for r in sd.riadky(kocka):
            if r["e_nuts13"] in kraje:
                vysl["kraje"][r["e_nuts13"]].setdefault(druh, {})[r["e_year"]] = r["hodnota"]
    for r in sd.riadky("om7002rr"):
        if r["e_nuts14"] in kraje:
            vysl["obyvatelia"][r["e_nuts14"]][r["e_year"]] = r["hodnota"]
    print("Kriminalita: " + ", ".join(f"{k} {max(v.get('Trestné činy spolu', {'-': 0}).items())}" for k, v in vysl["kraje"].items()))
    return vysl


def zluc_skoly(stare: dict | None, nove: dict) -> dict:
    """Staršie roky (DATAcube od 1996) + nové zo STATdata (od 2013, prepisujú)."""
    out = {s: {d: dict(r) for d, r in (v or {}).items()} for s, v in (stare or {}).items()}
    for s, druhy in nove.items():
        for d, roky in druhy.items():
            out.setdefault(s, {}).setdefault(d, {}).update(roky)
            out[s][d] = dict(sorted(out[s][d].items()))
    return out


def main() -> int:
    p = DATA / "mesta" / "temy.json"
    stare = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    vystup = {"zdroj": {"nazov": "Štatistický úrad SR – STATdata", "url": sd.WEB}}
    chyby = 0
    for kluc, f in (("skoly", lambda: zluc_skoly(stare.get("skoly"), skoly())), ("skoly_mapa", skoly_mapa),
                    ("mestske", lambda: mestske(stare.get("mestske"))), ("kriminalita", lambda: kriminalita(stare.get("kriminalita")))):
        try:
            vystup[kluc] = f()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            import traceback
            traceback.print_exc()
            print(f"::warning title=Témy miest {kluc}::{e!r}")
            vystup[kluc] = stare.get(kluc)
    if chyby == 4:
        raise RuntimeError("Témy miest: všetky moduly zlyhali")
    vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zapis_ak_zmena(p, vystup)
    return 0


if __name__ == "__main__":
    spusti(main, "Témy miest (STATdata)")
