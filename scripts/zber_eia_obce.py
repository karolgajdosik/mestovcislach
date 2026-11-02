"""Zámery v posudzovaní vplyvov na životné prostredie (EIA/SEA) vo všetkých obciach SR.

Zdroj: Enviroportál MŽP SR / SAŽP, verejné API https://www.enviroportal.sk/api/eia_projects – zoznam obsahuje
kraj, okres a obec zámeru. Prejde sa celý zoznam (~190 strán po 100); detail sa nesťahuje,
navrhovateľa preto neukladáme vôbec. Krajské mestá majú podrobný zber (zber_eia.py).

Výstup: data/obce/eia.json  {kod: {spolu, aktivne, zamery: [[seo, nazov, stav, zmena, typ, kat, ukoncene], …]}}
"""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

from spolocne import DATA, bez_diakritiky, s, spusti, zapis_ak_zmena
from zber_eia import AKTIVNE_ROKY, API, LEN_SEA, NA_STRANU, UKONCENE, WEB, ciste, kategoria

VYSTUP = DATA / "obce" / "eia.json"
NA_OBEC = 12


def kluc(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", bez_diakritiky(t or "").lower()).strip()


def main() -> int:
    zoz = json.loads((DATA / "obce" / "zoznam.json").read_text(encoding="utf-8"))
    zoz = zoz["obce"] if isinstance(zoz, dict) else zoz
    podla = {(kluc(o["okres"]), kluc(o["nazov"])): o["kod"] for o in zoz}
    podla_mena: dict[str, list] = defaultdict(list)
    for o in zoz:
        podla_mena[kluc(o["nazov"])].append(o["kod"])

    hranica = (date.today() - timedelta(days=365 * AKTIVNE_ROKY)).isoformat()
    po_obci: dict[str, list] = defaultdict(list)
    strana, poloziek, bez_obce = 1, 0, 0
    while True:
        for pokus in range(4):
            try:
                r = s.get(API, params={"page": strana, "itemsPerPage": NA_STRANU}, headers={"Accept": "application/json"}, timeout=120)
                r.raise_for_status()
                break
            except Exception as e:  # noqa: BLE001
                print(f"strana {strana}: {e}")
                time.sleep(10 * (pokus + 1))
        else:
            raise RuntimeError(f"EIA zoznam: strana {strana} nedostupná")
        j = r.json()
        polozky = j.get("data") or []
        if not polozky:
            break
        for z in polozky:
            poloziek += 1
            obec = re.sub(r"\s+", " ", z.get("obec") or "").strip()
            # „Košice - Juh“, viac obcí oddelených čiarkou – berieme prvú
            obec = re.split(r"[,;]| - ", obec)[0].strip()
            kod = podla.get((kluc(z.get("okres")), kluc(obec)))
            if not kod and len(podla_mena.get(kluc(obec), [])) == 1:
                kod = podla_mena[kluc(obec)][0]
            if not kod:
                bez_obce += 1
                continue
            nazov = ciste(z.get("name"))
            sea = bool(LEN_SEA.search(z.get("zbierka") or ""))
            stav = ciste(z.get("stav"))
            zmena = (z.get("datumPoslednejZmeny") or "")[:10]
            po_obci[kod].append([z["seoId"], nazov[:200], stav, zmena, "SEA" if sea else "EIA", kategoria(nazov, "", sea),
                                 bool(UKONCENE.search(stav)) or zmena < hranica])
        if strana >= int((j.get("meta") or {}).get("last_page") or strana):
            break
        strana += 1
        time.sleep(0.3)
    print(f"EIA: {strana} strán, {poloziek} zámerov, bez priradenej obce {bez_obce}, obcí so zámermi {len(po_obci)}")
    if poloziek < 10000 or len(po_obci) < 1000:
        raise RuntimeError("EIA: podozrivo málo zámerov")
    out = {}
    for kod, zz in sorted(po_obci.items()):
        zz.sort(key=lambda x: x[3], reverse=True)
        out[kod] = {"spolu": len(zz), "aktivne": sum(not x[6] for x in zz), "zamery": zz[:NA_OBEC]}
    zapis_ak_zmena(VYSTUP, {"aktualizovane": datetime.now().isoformat(timespec="seconds"), "web": WEB,
                            "zdroj": {"nazov": "Enviroportál MŽP SR / SAŽP – Informačný systém EIA/SEA", "url": "https://www.enviroportal.sk/eia"},
                            "obce": out}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "EIA vo všetkých obciach")
