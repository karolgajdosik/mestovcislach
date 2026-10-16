"""Zmluvy krajských miest bez vlastného portálu otvorených dát z Centrálneho registra zmlúv (CRZ).

Zdroj: denné exporty CRZ https://www.crz.gov.sk/export/RRRR-MM-DD.zip. Mesto spoznáme podľa IČO (src/mesta.json, pole „ico“)
na ktorejkoľvek strane zmluvy – druhá strana je partner. Bratislava (mestské časti – zber_zmluvy_mc.py) a Košice
(portál mesta – zber_samosprava_mesta.py) majú vlastné zdroje.

GDPR: partnera zverejňujeme menom len ak je to právnická osoba alebo inštitúcia (podľa právnej formy v názve);
zmluvy s fyzickými osobami (aj živnostníkmi) len započítavame do súčtov – bez mena a predmetu.

Spracované zmluvy: data/zmluvy-mesta/<rok>.json, posledný deň: data/zmluvy-mesta/stav.json (ďalší beh len nové dni).
Výstup: data/mesta/crz-<slug>.json – súhrny pre stránku /<slug>/samosprava a asistenta.
"""

from __future__ import annotations

import io
import json
import re
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from spolocne import DATA, KOREN, s, spusti, zapis_ak_zmena
from zber_zmluvy_mc import KONTAKT, POSKYTOVATEL, PRAVNA_FORMA, cislo, text

OD = date(2022, 1, 1)
ULOZISKO = DATA / "zmluvy-mesta"
VLASTNY_ZDROJ = {"bratislava", "kosice"}
MESTA = [m for m in json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8")) if m.get("ico") and m["slug"] not in VLASTNY_ZDROJ]
PODLA_ICO = {m["ico"]: m["slug"] for m in MESTA}
MAX_DNI = 2000  # jeden beh (prvý beh ~1 hodina)


def ico(x: str) -> str:
    i = re.sub(r"\D", "", x or "")
    return i.zfill(8) if 6 <= len(i) <= 8 else ""


def spracuj_den(d: date, zmluvy: dict) -> int:
    r = s.get(f"https://www.crz.gov.sk/export/{d.isoformat()}.zip", timeout=120)
    if r.status_code == 404:
        return 0
    r.raise_for_status()
    n = 0
    z = zipfile.ZipFile(io.BytesIO(r.content))
    for meno in z.namelist():
        xml = z.read(meno).decode("utf-8", "replace")
        for blok in re.findall(r"<zmluva>(.*?)</zmluva>", xml, re.S):
            if not any(i in blok for i in PODLA_ICO):  # rýchly filter
                continue
            p = {k: v for k, v in re.findall(r"<(\w+)>(.*?)</\1>", re.sub(r"<prilohy>.*?</prilohy>", "", blok, flags=re.S), re.S)}
            i1, i2 = ico(p.get("ico1", "")), ico(p.get("ico", ""))
            if i1 in PODLA_ICO:
                mesto, partner, ico_p = PODLA_ICO[i1], text(p.get("zs2", "")), i2
            elif i2 in PODLA_ICO:
                mesto, partner, ico_p = PODLA_ICO[i2], text(p.get("zs1", "")), i1
            else:
                continue
            podpis = (p.get("datum") or "")[:10]
            if not podpis or podpis.startswith("0000") or podpis < OD.isoformat() or podpis > date.today().isoformat():
                podpis = (p.get("datum_zverejnene") or "")[:10]
            if not podpis or podpis < OD.isoformat():
                continue
            suma = cislo(p.get("suma_spolu") or p.get("suma_zmluva"))
            organizacia = bool(PRAVNA_FORMA.search(partner))
            predmet = text(p.get("predmet", "")) or text(p.get("nazov", ""))
            zmluvy[p["ID"]] = {
                "id": p["ID"], "d": podpis, "m": mesto, "s": suma,
                "p": partner[:120] if organizacia else None, "ico": ico_p if organizacia else None,
                "pr": KONTAKT.sub("…", predmet)[:200] if organizacia else None,
                "dot": organizacia and bool(re.search(r"dotáci|grant", predmet + " " + text(p.get("nazov", "")), re.I)),
            }
            n += 1
    return n


def nacitaj() -> tuple[dict, dict]:
    ULOZISKO.mkdir(parents=True, exist_ok=True)
    stav_subor = ULOZISKO / "stav.json"
    stav = json.loads(stav_subor.read_text(encoding="utf-8")) if stav_subor.exists() else {"posledny_den": None}
    zmluvy = {}
    for f in sorted(ULOZISKO.glob("20*.json")):
        zmluvy.update(json.loads(f.read_text(encoding="utf-8")))
    return stav, zmluvy


def uloz(stav: dict, zmluvy: dict) -> None:
    po_rokoch: dict[str, dict] = defaultdict(dict)
    for k, z in zmluvy.items():
        po_rokoch[z["d"][:4]][k] = z
    for rok, zz in po_rokoch.items():
        zapis_ak_zmena(ULOZISKO / f"{rok}.json", dict(sorted(zz.items())), kompaktne=True)
    (ULOZISKO / "stav.json").write_text(json.dumps(stav, ensure_ascii=False), encoding="utf-8")


def suhrn_mesta(zz: list[dict]) -> dict:
    dnes = date.today()
    roky: dict[str, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0, "fo_pocet": 0, "fo_suma": 0.0})
    partneri: dict[str, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0})
    for z in zz:
        r = roky[z["d"][:4]]
        r["pocet"] += 1
        r["suma"] += z["s"]
        if not z["p"]:
            r["fo_pocet"] += 1
            r["fo_suma"] += z["s"]
            continue
        if int(z["d"][:4]) >= dnes.year - 2:
            k = z["ico"] or z["p"].lower()
            partneri[k]["nazov"] = z["p"]
            partneri[k]["pocet"] += 1
            partneri[k]["suma"] += z["s"]
    hranica = (dnes - timedelta(days=365)).isoformat()
    dot = [z for z in zz if z["dot"]]
    poskytnute: dict[str, float] = defaultdict(float)
    for z in dot:
        if not POSKYTOVATEL.search(z["p"]):
            poskytnute[z["p"]] += z["s"]
    return {
        "typ": "zmluvy", "zaznamov": len(zz), "skryte_fyzicke_osoby": sum(1 for z in zz if not z["p"]),
        "roky": {k: {"pocet": v["pocet"], "suma": round(v["suma"]), "fo_pocet": v["fo_pocet"], "fo_suma": round(v["fo_suma"])} for k, v in sorted(roky.items())},
        "dodavatelia_posledne_3_roky": sorted(({"ico": k if k.isdigit() else None, "nazov": v["nazov"], "pocet": v["pocet"], "suma": round(v["suma"])} for k, v in partneri.items()),
                                              key=lambda x: -x["suma"])[:20],
        "najvacsie_12_mesiacov": [{"datum": z["d"], "dodavatel": z["p"], "ico": z["ico"], "suma": z["s"], "popis": z["pr"] or "",
                                   "url": f"https://www.crz.gov.sk/zmluva/{z['id']}/"}
                                  for z in sorted((z for z in zz if z["p"] and z["d"] >= hranica), key=lambda z: -z["s"])[:15]],
        "dotacie_poskytnute": [{"nazov": n, "suma": round(v)} for n, v in sorted(poskytnute.items(), key=lambda x: -x[1])[:15]],
    }


def main() -> int:
    stav, zmluvy = nacitaj()
    d = date.fromisoformat(stav["posledny_den"]) + timedelta(days=1) if stav["posledny_den"] else OD
    dnes, chyby, spracovane, dni = date.today(), 0, 0, 0
    while d < dnes and dni < MAX_DNI:
        try:
            spracovane += spracuj_den(d, zmluvy)
            stav["posledny_den"] = d.isoformat()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=CRZ mestá::{d}: {e}")
            if chyby > 20:
                break
            time.sleep(5)
            continue  # deň skúsime znova (max. 20 chýb)
        if d.day == 1:
            print(f"{d}: spolu {len(zmluvy)} zmlúv")
            uloz(stav, zmluvy)
        d += timedelta(days=1)
        dni += 1
    print(f"Nové/zmenené zmluvy: {spracovane}, spolu {len(zmluvy)}, posledný deň {stav['posledny_den']}")
    uloz(stav, zmluvy)
    if len(zmluvy) < 500:
        raise RuntimeError(f"Málo zmlúv ({len(zmluvy)})")
    po_meste: dict[str, list] = defaultdict(list)
    for z in zmluvy.values():
        po_meste[z["m"]].append(z)
    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for m in MESTA:
        zz = po_meste.get(m["slug"], [])
        if len(zz) < 50:
            print(f"::warning title=CRZ {m['nazov']}::len {len(zz)} zmlúv")
            continue
        zapis_ak_zmena(DATA / "mesta" / f"crz-{m['slug']}.json", {
            "mesto": m["slug"], "ico": m["ico"], "od": OD.isoformat(), "do": stav["posledny_den"],
            "zdroj": {"nazov": "Centrálny register zmlúv (CRZ)", "url": "https://www.crz.gov.sk"},
            "zmluvy": {**suhrn_mesta(zz), "zdroj": "https://www.crz.gov.sk"},
            "aktualizovane": teraz,
        })
        print(f"{m['nazov']}: {len(zz)} zmlúv, {round(sum(z['s'] for z in zz)):,} €")
    return 0


if __name__ == "__main__":
    spusti(main, "Zmluvy krajských miest z CRZ")
