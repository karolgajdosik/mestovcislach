"""Zmluvy všetkých obcí a miest SR z Centrálneho registra zmlúv (CRZ) – súhrny pre stránky /<kraj>/<okres>/<obec>.

Obce nemusia zmluvy zverejňovať v CRZ (môžu na vlastnom webe), preto ide len o zmluvy, ktoré v CRZ sú – zverejnené
obcou alebo jej zmluvným partnerom (napr. ministerstvom pri dotácii).

IČO obcí: Register právnických osôb (api.statistics.sk/rpo) – hľadanie „Obec X“ / „Mesto X“, zhoda podľa kódu obce
v adrese sídla. Uložené v data/obce/ico.json (doplňuje sa len chýbajúce).

GDPR: partnera zverejňujeme menom len ak je to právnická osoba alebo inštitúcia (podľa právnej formy v názve);
zmluvy s fyzickými osobami (aj živnostníkmi) len započítavame – bez mena a predmetu.

Spracované zmluvy: data/zmluvy-obce/<rok-mesiac>.json (kompaktné), posledný deň: data/zmluvy-obce/stav.json.
Výstup: data/obce/zmluvy.json  {kod: {roky, fo, partneri, najvacsie}}
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
from zber_zmluvy_mc import KONTAKT, PRAVNA_FORMA, cislo, text

OD = date(2025, 1, 1)
ULOZISKO = DATA / "zmluvy-obce"
ICO_SUBOR = DATA / "obce" / "ico.json"
VYSTUP = DATA / "obce" / "zmluvy.json"
RPO = "https://api.statistics.sk/rpo/v1/search"
MAX_DNI = 1000
MAX_RPO = 3200
PREDMET_OD = 5000  # predmet ukladáme len pri väčších zmluvách (menšie súbory)


def ico(x: str) -> str:
    i = re.sub(r"\D", "", x or "")
    return i.zfill(8) if 6 <= len(i) <= 8 else ""


def obce() -> list[dict]:
    zoz = json.loads((DATA / "obce" / "zoznam.json").read_text(encoding="utf-8"))
    return zoz["obce"] if isinstance(zoz, dict) else zoz


def najdi_ico(o: dict) -> str | None:
    nazov = re.sub(r"\s*\(.*\)$", "", o["nazov"])
    varianty = [nazov] + ([re.sub(r"\s*-\s*", "-", nazov)] if " - " in nazov else [])
    for predpona in ("Obec", "Mesto"):
        for n in varianty:
            meno = f"{predpona} {n}"
            for pokus in range(3):
                try:
                    r = s.get(RPO, params={"fullName": meno}, timeout=60)
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(5 * (pokus + 1))
            else:
                continue
            if r.status_code != 200:
                continue
            for v in r.json().get("results") or []:
                kody = {str((a.get("municipality") or {}).get("code") or "")[-6:] for a in v.get("addresses") or []}
                mena = {(x.get("value") or "").strip().lower() for x in v.get("fullNames") or []}
                if o["kod"] in kody and meno.lower() in mena and not v.get("termination"):
                    i = ico((v.get("identifiers") or [{}])[-1].get("value", ""))
                    if i:
                        return i
    return None


def doplni_ica(zoznam: list[dict]) -> dict[str, str]:
    """IČO obcí z RPO (4 súbežné dotazy – jeden trvá aj niekoľko sekúnd); priebežne ukladá."""
    from concurrent.futures import ThreadPoolExecutor

    ica: dict[str, str] = json.loads(ICO_SUBOR.read_text(encoding="utf-8")) if ICO_SUBOR.exists() else {}
    chyba = [o for o in zoznam if o["kod"] not in ica][:MAX_RPO]
    with ThreadPoolExecutor(4) as ex:
        for n, (o, i) in enumerate(zip(chyba, ex.map(najdi_ico, chyba)), 1):
            if i:
                ica[o["kod"]] = i
            if n % 200 == 0:
                ICO_SUBOR.write_text(json.dumps(dict(sorted(ica.items())), ensure_ascii=False, indent=0), encoding="utf-8")
                print(f"  RPO {n}/{len(chyba)}")
    ICO_SUBOR.write_text(json.dumps(dict(sorted(ica.items())), ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"IČO obcí: {len(ica)} z {len(zoznam)}; bez IČO napr.: {[o['nazov'] for o in zoznam if o['kod'] not in ica][:10]}")
    return ica


def spracuj_den(d: date, podla_ico: dict[str, str], zmluvy: dict) -> int:
    r = s.get(f"https://www.crz.gov.sk/export/{d.isoformat()}.zip", timeout=120)
    if r.status_code == 404:
        return 0
    r.raise_for_status()
    n = 0
    z = zipfile.ZipFile(io.BytesIO(r.content))
    for meno in z.namelist():
        xml = z.read(meno).decode("utf-8", "replace")
        for blok in re.findall(r"<zmluva>(.*?)</zmluva>", xml, re.S):
            p = {k: v for k, v in re.findall(r"<(\w+)>(.*?)</\1>", re.sub(r"<prilohy>.*?</prilohy>", "", blok, flags=re.S), re.S)}
            i1, i2 = ico(p.get("ico1", "")), ico(p.get("ico", ""))
            if i1 in podla_ico:
                kod, partner, ico_p = podla_ico[i1], text(p.get("zs2", "")), i2
            elif i2 in podla_ico:
                kod, partner, ico_p = podla_ico[i2], text(p.get("zs1", "")), i1
            else:
                continue
            podpis = (p.get("datum") or "")[:10]
            if not podpis or podpis.startswith("0000") or podpis < OD.isoformat() or podpis > date.today().isoformat():
                podpis = (p.get("datum_zverejnene") or "")[:10]
            if not podpis or podpis < OD.isoformat():
                continue
            suma = cislo(p.get("suma_spolu") or p.get("suma_zmluva"))
            org = bool(PRAVNA_FORMA.search(partner))
            zaz = {"d": podpis, "k": kod, "s": suma}
            if org:
                zaz["p"] = partner[:100]
                if ico_p:
                    zaz["i"] = ico_p
                if suma >= PREDMET_OD:
                    zaz["pr"] = KONTAKT.sub("…", text(p.get("predmet", "")) or text(p.get("nazov", "")))[:160]
            zmluvy[p["ID"]] = zaz
            n += 1
    return n


def nacitaj() -> tuple[dict, dict]:
    ULOZISKO.mkdir(parents=True, exist_ok=True)
    stav_subor = ULOZISKO / "stav.json"
    stav = json.loads(stav_subor.read_text(encoding="utf-8")) if stav_subor.exists() else {"posledny_den": None}
    zmluvy: dict = {}
    for f in sorted(ULOZISKO.glob("20*.json")):
        zmluvy.update(json.loads(f.read_text(encoding="utf-8")))
    return stav, zmluvy


def uloz(stav: dict, zmluvy: dict) -> None:
    po_mesiacoch: dict[str, dict] = defaultdict(dict)
    for k, z in zmluvy.items():
        po_mesiacoch[z["d"][:7]][k] = z
    for m, zz in po_mesiacoch.items():
        zapis_ak_zmena(ULOZISKO / f"{m}.json", dict(sorted(zz.items())), kompaktne=True)
    (ULOZISKO / "stav.json").write_text(json.dumps(stav, ensure_ascii=False), encoding="utf-8")


def suhrn(zz: list[tuple[str, dict]]) -> dict:
    dnes = date.today()
    hranica = (dnes - timedelta(days=365)).isoformat()
    od_partneri = (dnes - timedelta(days=730)).isoformat()
    roky: dict[str, list] = defaultdict(lambda: [0, 0.0])
    fo = [0, 0.0]
    partneri: dict[str, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0})
    for _, z in zz:
        roky[z["d"][:4]][0] += 1
        roky[z["d"][:4]][1] += z["s"]
        if "p" not in z:
            fo[0] += 1
            fo[1] += z["s"]
            continue
        if z["d"] >= od_partneri:
            k = z.get("i") or z["p"].lower()
            partneri[k]["nazov"] = z["p"]
            partneri[k]["pocet"] += 1
            partneri[k]["suma"] += z["s"]
    return {
        "roky": {r: [v[0], round(v[1])] for r, v in sorted(roky.items())},
        "fo": [fo[0], round(fo[1])],
        "partneri": [[v["nazov"], v["pocet"], round(v["suma"])] for v in sorted(partneri.values(), key=lambda v: -v["suma"])[:6]],
        "najvacsie": [[z["d"], z["p"], round(z["s"]), z.get("pr") or "", zid]
                      for zid, z in sorted((x for x in zz if "p" in x[1] and x[1]["d"] >= hranica), key=lambda x: -x[1]["s"])[:5] if z["s"] > 0],
    }


def main() -> int:
    zoznam = obce()
    ica = doplni_ica(zoznam)
    if len(ica) < 2500:
        print(f"::warning title=Zmluvy obcí::IČO len pre {len(ica)} obcí")
    krajske = {m["ico"] for m in json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8")) if m.get("ico")}
    podla_ico = {i: k for k, i in ica.items() if i not in krajske}

    stav, zmluvy = nacitaj()
    d = date.fromisoformat(stav["posledny_den"]) + timedelta(days=1) if stav["posledny_den"] else OD
    dnes, chyby, spracovane, dni = date.today(), 0, 0, 0
    while d < dnes and dni < MAX_DNI:
        try:
            spracovane += spracuj_den(d, podla_ico, zmluvy)
            stav["posledny_den"] = d.isoformat()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=CRZ obce::{d}: {e}")
            if chyby > 30:
                break
            time.sleep(10 * min(chyby, 6))
            continue
        if d.day == 1:
            print(f"{d}: spolu {len(zmluvy)} zmlúv")
            uloz(stav, zmluvy)
        d += timedelta(days=1)
        dni += 1
        time.sleep(0.5)
    print(f"Nové/zmenené zmluvy: {spracovane}, spolu {len(zmluvy)}, posledný deň {stav['posledny_den']}")
    uloz(stav, zmluvy)
    if len(zmluvy) < 10000:
        raise RuntimeError(f"Málo zmlúv obcí ({len(zmluvy)})")

    po_obci: dict[str, list] = defaultdict(list)
    for zid, z in zmluvy.items():
        po_obci[z["k"]].append((zid, z))
    zapis_ak_zmena(VYSTUP, {
        "od": OD.isoformat(), "do": stav["posledny_den"], "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "zdroj": {"nazov": "Centrálny register zmlúv (CRZ)", "url": "https://www.crz.gov.sk"},
        "obce": {k: suhrn(zz) for k, zz in sorted(po_obci.items())},
    }, kompaktne=True)
    print(f"Obce so zmluvami v CRZ: {len(po_obci)} z {len(podla_ico)}")
    return 0


if __name__ == "__main__":
    spusti(main, "Zmluvy obcí z CRZ")
