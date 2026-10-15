"""Zmluvy mestských častí Bratislavy a dotácie z Centrálneho registra zmlúv (CRZ).

Zdroj: denné exporty CRZ https://www.crz.gov.sk/export/RRRR-MM-DD.zip (XML so zmluvami zmenenými v daný deň).
Pole zs1 = zmluvná strana 1 (spravidla zverejňujúca inštitúcia, IČO v ico1), zs2 = zmluvná strana 2 (IČO v ico).
Mestská časť môže byť na ktorejkoľvek strane – druhá strana je partner.

GDPR: partnera zverejňujeme menom len ak je to právnická osoba alebo inštitúcia (podľa právnej formy v názve).
Zmluvy s fyzickými osobami (aj živnostníkmi) len započítavame do súčtov – bez mena a predmetu.

Spracované zmluvy sa ukladajú po rokoch do data/zmluvy-mc/<rok>.json (mení sa len súbor aktuálneho roka),
posledný spracovaný deň do data/zmluvy-mc/stav.json – ďalší beh sťahuje len nové dni.
Výstupy: data/zmluvy-mc.json (súhrny pre /financie a asistenta), public/data/zmluvy-mc/<mč>.json (zoznamy pre vyhľadávanie)
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from html import unescape

from spolocne import DATA, VEREJNE, bez_diakritiky, norm_mc, s, spusti, zapis_ak_zmena

OD = date(2022, 1, 1)
ULOZISKO = DATA / "zmluvy-mc"
MESTO = "Hlavné mesto"
# Právna forma alebo inštitúcia – celé slová (inak by „Klub“ zachytilo priezvisko Klubal, „fond“ Fondová)
PRAVNA_FORMA = re.compile(r"s\.\s?r\.\s?o|spol\.|\ba\.\s?s\.|\bk\.\s?s\.|v\.\s?o\.\s?s|\bn\.\s?o\.|\bo\.\s?z\.|z\.\s?p\.\s?o|š\.\s?p\.|\bp\.\s?o\.|o\.\s?c\.\s?z|\b(?:gmbh|ltd|inc|"
                          r"mesto|mestsk\w*|obec|kraj|samosprávny|ministerstvo|úrad|univerzita|ústav|inštitút|nadácia|fond|cirkev|cirkevný|farnosť|zbor|zväz|združenie|spolok|"
                          r"klub|komora|banka|poisťovňa|slovensk\w*|podnik|agentúra|správa|škola|školsk\w*|gymnázium|materská|jasle|centrum|zariadenie|divadlo|"
                          r"múzeum|galéria|knižnica|polícia|hasičský|nemocnica|poliklinika|festival|jednota|akadémia|spoločenstvo|vlastníkov|družstvo|dpb|olo|bvs|zsd|spp)\b", re.I)
POSKYTOVATEL = re.compile(r"ministerstv|úrad|samosprávny kraj|hlavné mesto|\bfond|nadáci|agentúr|európsk|program|správa|environmentáln|slovenský zväz|olympijsk", re.I)
KONTAKT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(\+421|0)\s?\d{3}\s?\d{3}\s?\d{3}")


def strana_mc(nazov: str) -> str | None:
    n = re.sub(r"\s+", " ", unescape(nazov or "")).strip()
    nb = bez_diakritiky(n).lower()
    if re.search(r"hlavn\w* mest\w*.*bratislav", nb) and "mestska cast" not in nb:
        return MESTO
    if not re.search(r"mestsk\w* cast|\bmc\b", nb) or "bratislav" not in nb or "kosic" in nb:
        return None
    return norm_mc(n.split(",")[0].strip())


def text(x: str) -> str:
    return re.sub(r"\s+", " ", unescape(x or "")).strip()


def cislo(x: str) -> float:
    try:
        return round(float((x or "0").replace(",", ".")), 2)
    except ValueError:
        return 0.0


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
            p = {k: v for k, v in re.findall(r"<(\w+)>(.*?)</\1>", re.sub(r"<prilohy>.*?</prilohy>", "", blok, flags=re.S), re.S)}
            mc1, mc2 = strana_mc(p.get("zs1", "")), strana_mc(p.get("zs2", ""))
            if not (mc1 or mc2):
                continue
            mc, partner, ico = (mc1, p.get("zs2", ""), p.get("ico", "")) if mc1 else (mc2, p.get("zs1", ""), p.get("ico1", ""))
            partner = text(partner)
            ico = re.sub(r"\D", "", ico or "")
            ico = ico if 6 <= len(ico) <= 8 else ""
            podpis = (p.get("datum") or "")[:10]
            if not podpis or podpis < OD.isoformat() or podpis.startswith("0000"):
                podpis = (p.get("datum_zverejnene") or "")[:10]
            if podpis > date.today().isoformat():  # preklep v dátume podpisu (napr. 2028) → dátum zverejnenia
                podpis = (p.get("datum_zverejnene") or "")[:10]
            if podpis < OD.isoformat():
                continue
            predmet = text(p.get("predmet", ""))
            organizacia = bool(PRAVNA_FORMA.search(partner)) or bool(strana_mc(partner))
            if not organizacia:  # fyzická osoba: len do súčtov
                zmluvy[p["ID"]] = {"id": p["ID"], "d": podpis, "mc": mc, "p": None, "ico": None, "pr": None, "s": cislo(p.get("suma_spolu") or p.get("suma_zmluva")), "dot": False, "mc_mc": False}
                n += 1
                continue
            zmluvy[p["ID"]] = {
                "id": p["ID"], "d": podpis, "mc": mc,
                "p": partner[:120] if organizacia else None, "ico": ico if organizacia else None,
                "pr": KONTAKT.sub("…", predmet)[:220] if organizacia else None,
                "s": cislo(p.get("suma_spolu") or p.get("suma_zmluva")),
                "dot": bool(re.search(r"dotáci|grant", predmet + " " + text(p.get("nazov", "")), re.I)),
                "mc_mc": bool(strana_mc(partner)),
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
    # staršie záznamy s dátumom v budúcnosti (preklep v CRZ) – na posledný spracovaný deň
    for z in zmluvy.values():
        if stav.get("posledny_den") and z["d"] > stav["posledny_den"]:
            z["d"] = stav["posledny_den"]
    return stav, zmluvy


def uloz(stav: dict, zmluvy: dict) -> None:
    po_rokoch: dict[str, dict] = defaultdict(dict)
    for k, z in zmluvy.items():
        po_rokoch[z["d"][:4]][k] = z
    for rok, zz in po_rokoch.items():
        zapis_ak_zmena(ULOZISKO / f"{rok}.json", dict(sorted(zz.items())), kompaktne=True)
    for f in ULOZISKO.glob("20*.json"):
        if f.stem not in po_rokoch:
            f.unlink()
    (ULOZISKO / "stav.json").write_text(json.dumps(stav, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    stav, zmluvy = nacitaj()
    zaciatok = date.fromisoformat(stav["posledny_den"]) + timedelta(days=1) if stav["posledny_den"] else OD
    dnes = date.today()
    d, chyby, spracovane = zaciatok, 0, 0
    while d < dnes:
        try:
            spracovane += spracuj_den(d, zmluvy)
            stav["posledny_den"] = d.isoformat()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=CRZ::{d}: {e}")
            if chyby > 20:
                break
        if d.day == 1:
            print(f"{d}: spolu {len(zmluvy)} zmlúv")
            uloz(stav, zmluvy)
        d += timedelta(days=1)
    print(f"Nové/zmenené zmluvy: {spracovane}, spolu {len(zmluvy)}, posledný deň {stav['posledny_den']}")
    if len(zmluvy) < 1000:
        raise RuntimeError(f"Málo zmlúv ({len(zmluvy)})")
    uloz(stav, zmluvy)

    vsetky = sorted(zmluvy.values(), key=lambda z: z["d"], reverse=True)
    suhrn: dict = {"zdroj": {"nazov": "Centrálny register zmlúv (CRZ) – denné exporty", "url": "https://www.crz.gov.sk", "licencia": "verejné údaje podľa zákona č. 211/2000 Z. z."},
                   "od": OD.isoformat(), "do": stav["posledny_den"], "mestske_casti": {}, "dotacie": {}}
    po_mc: dict[str, list] = defaultdict(list)
    for z in vsetky:
        po_mc[z["mc"]].append(z)
    (VEREJNE / "zmluvy-mc").mkdir(parents=True, exist_ok=True)
    for mc, zz in sorted(po_mc.items()):
        roky, sumy, partneri, fyz = Counter(), Counter(), defaultdict(lambda: [0, 0.0, None]), [0, 0.0]
        for z in zz:
            roky[z["d"][:4]] += 1
            sumy[z["d"][:4]] += z["s"]
            if z["p"]:
                k = z["ico"] or z["p"].lower()
                partneri[k][0] += 1
                partneri[k][1] += z["s"]
                partneri[k][2] = partneri[k][2] or z["p"]
            else:
                fyz[0] += 1
                fyz[1] += z["s"]
        top = sorted(partneri.items(), key=lambda x: -x[1][1])[:15]
        dot = [z for z in zz if z["dot"] and z["p"]]
        suhrn["mestske_casti"][mc] = {
            "zmluv": len(zz), "suma": round(sum(z["s"] for z in zz)), "roky": {r: [roky[r], round(sumy[r])] for r in sorted(roky)},
            "fyzicke_osoby": {"zmluv": fyz[0], "suma": round(fyz[1])},
            "najvacsi_partneri": [{"nazov": v[2], "ico": k if k.isdigit() else None, "zmluv": v[0], "suma": round(v[1])} for k, v in top],
            "najvacsie_zmluvy": [{k: z[k] for k in ("id", "d", "p", "ico", "pr", "s")} for z in sorted((z for z in zz if z["p"]), key=lambda z: -z["s"])[:10]],
        }
        # smer dotácie podľa partnera: štát, kraj, mesto, fondy a nadácie dotácie poskytujú (MČ prijíma), ostatní ich od MČ dostávajú
        prijate = [z for z in dot if POSKYTOVATEL.search(z["p"])]
        dane = [z for z in dot if not POSKYTOVATEL.search(z["p"])]
        sumy_p: Counter = Counter()
        for z in dane:
            sumy_p[z["p"]] += z["s"]
        sumy_z: Counter = Counter()
        for z in prijate:
            sumy_z[z["p"]] += z["s"]
        suhrn["dotacie"][mc] = {
            "poskytnute": {"zmluv": len(dane), "suma": round(sum(z["s"] for z in dane)), "prijimatelia": [{"nazov": n, "suma": round(v)} for n, v in sumy_p.most_common(10)]},
            "prijate": {"zmluv": len(prijate), "suma": round(sum(z["s"] for z in prijate)), "poskytovatelia": [{"nazov": n, "suma": round(v)} for n, v in sumy_z.most_common(8)]},
        }
        zapis_ak_zmena(VEREJNE / "zmluvy-mc" / f"{bez_diakritiky(mc).lower().replace(' ', '-')}.json",
                       {"mc": mc, "od": OD.isoformat(), "do": stav["posledny_den"], "fyzicke_osoby": suhrn["mestske_casti"][mc]["fyzicke_osoby"],
                        # [id, dátum, partner, IČO, predmet, suma, dotácia]
                        "zmluvy": [[z["id"], z["d"], z["p"], z["ico"], z["pr"], z["s"], 1 if z["dot"] else 0] for z in zz if z["p"]]}, kompaktne=True)
        print(f"{mc}: {len(zz)} zmlúv, {round(sum(z['s'] for z in zz)):,} €, dotácie {len(dot)}")
    suhrn["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zapis_ak_zmena(DATA / "zmluvy-mc.json", suhrn)
    return 0


if __name__ == "__main__":
    spusti(main, "Zber zmlúv mestských častí z CRZ")
