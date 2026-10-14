"""Dáta z portálu otvorených dát hlavného mesta – data.bratislava.sk (ArcGIS Hub).

Výstupy:
  data/rozpocet-bratislava.json   – záverečný účet: príjmy, výdavky, programy, hospodárenie
  data/ovzdusie-bratislava.json   – PM10, PM2.5, ozón podľa monitorovacích staníc
  data/zmluvy-bratislava.json     – súhrny zmlúv magistrátu zverejnených od júla 2022

Každý dataset na portáli je ArcGIS Feature Service. Adresu služby zistíme
z metadát položky (arcgis.com/sharing/rest/content/items/<id>) a dáta
stiahneme cez /query (bez API kľúča, po stránkach).

Licencie (podľa metadát portálu): rozpočet a ovzdušie CC BY 4.0,
zmluvy CC BY-NC 4.0 (nekomerčné použitie s uvedením zdroja).
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
PORTAL = "https://data.bratislava.sk/datasets/"

session = requests.Session()
session.headers["User-Agent"] = UA


# --- ArcGIS Hub -------------------------------------------------------------

def polozka(item_id: str) -> dict:
    it = session.get(f"https://www.arcgis.com/sharing/rest/content/items/{item_id}", params={"f": "json"}, timeout=60).json()
    if "error" in it or not it.get("url"):
        raise RuntimeError(f"Položka {item_id}: nenašiel som adresu služby ({it.get('error')}).")
    licencia = re.sub(r"<[^>]+>", "", it.get("licenseInfo") or "").strip()
    return {
        "id": item_id,
        "nazov": it.get("title"),
        "licencia": licencia if len(licencia) < 40 else None,
        "url": PORTAL + item_id,
        "upravene": datetime.fromtimestamp(it["modified"] / 1000, timezone.utc).date().isoformat() if it.get("modified") else None,
        "_sluzba": it["url"] if it["url"].rstrip("/")[-1].isdigit() else it["url"].rstrip("/") + "/0",
    }


def riadky(item: dict, polia: str = "*") -> list[dict]:
    vysledok, offset = [], 0
    while True:
        r = session.get(
            item["_sluzba"] + "/query",
            params={"where": "1=1", "outFields": polia, "returnGeometry": "false", "f": "json",
                    "resultOffset": offset, "resultRecordCount": 1000, "orderByFields": "ObjectId"},
            timeout=120,
        ).json()
        if "error" in r:
            raise RuntimeError(f"{item['nazov']}: {r['error']}")
        davka = [f["attributes"] for f in r.get("features", [])]
        vysledok += davka
        if not davka or not r.get("exceededTransferLimit") and len(davka) < 1000:
            break
        offset += len(davka)
    return vysledok


def zdroj(item: dict) -> dict:
    return {k: v for k, v in item.items() if not k.startswith("_")}


def cislo(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).replace("\xa0", "").replace(" ", "").replace(",", "."))


def uloz(nazov: str, obsah: dict) -> None:
    subor = DATA / nazov
    if subor.exists():
        stary = json.loads(subor.read_text(encoding="utf-8"))
        stary.pop("aktualizovane", None)
        if stary == obsah:
            print(f"{nazov}: bez zmeny")
            return
    obsah = {**obsah, "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    subor.write_text(json.dumps(obsah, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{nazov}: uložené")


# --- Rozpočet (záverečný účet) ----------------------------------------------

ROZPOCET = {
    "prijmy": ("bed5ccdbd73c412fbdd52889176faa73", {
        "BEZNE_PRIJMY": "Bežné príjmy", "KAPITALOVE__PRIJMY": "Kapitálové príjmy",
        "PRIJMOVE_FINANCNE_OPERACIE": "Príjmové finančné operácie", "SPOLU": "Spolu"}),
    "prijmy_druh": ("e5a125565cf646d79c2e4ac583321033", {
        "DANOVE_PRIJMY": "Daňové príjmy", "NEDANOVE_PRIJMY_A_KAPITALOVE_PRIJMY": "Nedaňové a kapitálové príjmy",
        "GRANTY_A_TRANSFERY": "Granty a transfery", "PRIJMOVE_FINANCNE_OPERACIE": "Príjmové finančné operácie"}),
    "vydavky": ("e59ddd92918b480196ed6c215a965269", {
        "BEZNE_VYDAVKY": "Bežné výdavky", "KAPITALOVE_VYDAVKY": "Kapitálové výdavky",
        "VYDAVKOVE_FINANCNE_OPERACIE": "Výdavkové finančné operácie", "SPOLU": "Spolu"}),
    "programy": ("0cd89fe509b649dc810880504c798b9a", {
        "MOBILITA_A_VEREJNA_DOPRAVA": "Mobilita a verejná doprava",
        "VEREJNA_INFRASTRUKTURA": "Verejná infraštruktúra",
        "PORIADOK_A_BEZPECNOST": "Poriadok a bezpečnosť",
        "KULTURA_SPORT_PODPORA_SLUZIEB_A_CESTOVNEHO_RUCHU": "Kultúra, šport a cestovný ruch",
        "VZDELAVANIE_A_VOLNY_CAS": "Vzdelávanie a voľný čas",
        "SOCIALNA_POMOCT_A_SOCIALNE_SLUZBY": "Sociálna pomoc a služby",
        "EFEKTIVNA_A_TRANSPARENTNA_SAMOSPRAVA": "Efektívna a transparentná samospráva",
        "SPRAVA_A_NAKLADANIE_S_MAJETKOM": "Správa majetku"}),
    "hospodarenie": ("71c76459d7954119b2d87534350a1dbf", {
        "VYSLEDOK_HOSPODARENIA_BEZ_FINANCNYCH_OPERACII": "Bez finančných operácií",
        "VYSLEDOK_HOSPODARENIA_CELKOVO_S_FINANCNYMI_OPERACIAMI": "S finančnými operáciami"}),
}


def zber_rozpocet() -> None:
    vystup = {"jednotka": "EUR", "casti": {}}
    for kluc, (item_id, polia) in ROZPOCET.items():
        item = polozka(item_id)
        roky = {}
        for r in riadky(item):
            rok = str(r["ROK"]).strip()
            roky[rok] = {nazov: cislo(r.get(pole)) for pole, nazov in polia.items()}
        if not roky:
            raise RuntimeError(f"Rozpočet {kluc}: prázdne dáta.")
        vystup["casti"][kluc] = {"zdroj": zdroj(item), "polozky": list(polia.values()), "roky": dict(sorted(roky.items()))}
    uloz("rozpocet-bratislava.json", vystup)


# --- Ovzdušie ---------------------------------------------------------------

OVZDUSIE = {
    "pm10": ("08b4888537194726bffd6f0f5a55c21e", "PM10", "LIMITNA_HODNOTA_PM10",
             "Priemerná ročná koncentrácia PM10", "µg/m³"),
    "pm10_prekrocenia": ("c560d929407e47e59793a78da0fe49bb", "POCET_PREKROCENI", "LIMITNA_HODNOTA_PM10",
                         "Počet dní s prekročením denného limitu PM10", "dní"),
    "pm25": ("7146fc000f1544309fbaef06a4a70fa3", "PM2_5", "LIMITNA_HODNOTA_PM2_5",
             "Priemerná ročná koncentrácia PM2,5", "µg/m³"),
    "o3": ("6e18d5a0c0fd466dab5bd821a744178a", "POCET_DNI_S_PREKROCENIM", "LIMITNA_HODNOTA_O3",
           "Počet dní s prekročením cieľovej hodnoty ozónu", "dní"),
}


def zber_ovzdusie() -> None:
    vystup = {"ukazovatele": {}}
    for kluc, (item_id, pole, pole_limit, popis, jednotka) in OVZDUSIE.items():
        item = polozka(item_id)
        stanice: dict[str, dict] = defaultdict(dict)
        limit = None
        for r in riadky(item):
            hodnota = cislo(r.get(pole))
            if hodnota is None:
                continue
            stanice[r["MONITOROVACIA_STANICA"].strip()][str(r["ROK"]).strip()] = hodnota
            limit = cislo(r.get(pole_limit)) or limit
        if not stanice:
            raise RuntimeError(f"Ovzdušie {kluc}: prázdne dáta.")
        vystup["ukazovatele"][kluc] = {
            "popis": popis, "jednotka": jednotka, "limit": limit, "zdroj": zdroj(item),
            "stanice": {s: dict(sorted(v.items())) for s, v in sorted(stanice.items())},
        }
    uloz("ovzdusie-bratislava.json", vystup)


# --- Zmluvy -----------------------------------------------------------------

ZMLUVY_ID = "dec22cd06721435d81161b9067556c3a"


def zber_zmluvy() -> None:
    item = polozka(ZMLUVY_ID)
    data = riadky(item)
    if len(data) < 1000:
        raise RuntimeError(f"Zmluvy: podozrivo málo záznamov ({len(data)}).")
    teraz = datetime.now(timezone.utc)
    pred_rokom = teraz - timedelta(days=365)

    po_rokoch: dict[str, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0})
    dodavatelia: dict[str, dict] = {}
    utvary: dict[str, float] = defaultdict(float)
    najvacsie = []
    bez_ico_suma = 0.0

    for r in data:
        if not r.get("DÁTUM_ZVEREJNENIA"):
            continue
        zverejnene = datetime.fromtimestamp(r["DÁTUM_ZVEREJNENIA"] / 1000, timezone.utc)
        suma = cislo(r.get("CELKOVÁ_SUMA_V_EUR")) or 0.0
        rok = str(zverejnene.year)
        po_rokoch[rok]["pocet"] += 1
        po_rokoch[rok]["suma"] += suma
        if zverejnene < pred_rokom:
            continue
        # Posledných 12 mesiacov. Mená zobrazujeme len pri subjektoch s IČO
        # (fyzické osoby bez IČO nezverejňujeme – GDPR).
        ico = (r.get("IČO_DODÁVATEĽA") or "").strip()
        utvary[(r.get("NÁZOV_ORGANIZAČNÉHO_ÚTVARU_SAMO") or "Neuvedené").strip()] += suma
        if not ico or not ico.isdigit():
            bez_ico_suma += suma
            continue
        d = dodavatelia.setdefault(ico, {"ico": ico, "nazov": (r.get("NÁZOV_DODÁVATEĽA") or "").strip(), "pocet": 0, "suma": 0.0})
        d["pocet"] += 1
        d["suma"] += suma
        if suma > 0:
            najvacsie.append({
                "datum": zverejnene.date().isoformat(),
                "dodavatel": d["nazov"],
                "ico": ico,
                "predmet": re.sub(r"\s+", " ", (r.get("PREDMET_ZMLUVY") or "")).strip()[:200],
                "suma": round(suma, 2),
                "utvar": (r.get("NÁZOV_ORGANIZAČNÉHO_ÚTVARU_SAMO") or "").strip(),
                "odkaz": (r.get("ODKAZ_NA_ZVEREJNENÚ_ZMLUVU") or "").strip(),
            })

    najvacsie.sort(key=lambda z: -z["suma"])
    top_dod = sorted(dodavatelia.values(), key=lambda d: -d["suma"])[:15]
    for d in top_dod:
        d["suma"] = round(d["suma"], 2)
    vystup = {
        "zdroj": zdroj(item),
        "pocet_spolu": len(data),
        "po_rokoch": {k: {"pocet": v["pocet"], "suma": round(v["suma"], 2)} for k, v in sorted(po_rokoch.items())},
        "posledny_rok": {
            "od": pred_rokom.date().isoformat(),
            "suma_bez_ico": round(bez_ico_suma, 2),
            "dodavatelia": top_dod,
            "utvary": [{"nazov": k, "suma": round(v, 2)} for k, v in sorted(utvary.items(), key=lambda x: -x[1])[:12]],
            "najvacsie": najvacsie[:20],
        },
    }
    uloz("zmluvy-bratislava.json", vystup)


def main() -> int:
    chyby = []
    for nazov, funkcia in [("rozpočet", zber_rozpocet), ("ovzdušie", zber_ovzdusie), ("zmluvy", zber_zmluvy)]:
        try:
            funkcia()
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{nazov}: {type(e).__name__}: {e}")
    if chyby:
        raise RuntimeError(" | ".join(chyby))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber data.bratislava.sk::{sprava}")
        sys.exit(1)
