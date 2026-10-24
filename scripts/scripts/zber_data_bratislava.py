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
           "Počet dní s prekročením cielovej hodnoty ozónu", "dní"),
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
ICO_MESTA = "603481"  # zmluvy, kde je mesto samo „dodávateľom“ (napr. príjmové), do rebríčkov nepočítame


def zber_zmluvy() -> None:
    item = polozka(ZMLUVY_ID)
    data, videne = [], set()
    for r in riadky(item):
        # Zdroj obsahuje niektoré zmluvy viackrát – rovnaký identifikátor aj odkaz.
        kluc = ((r.get("IDENTIFIKÁTOR_ZMLUVY") or "").strip(), (r.get("ODKAZ_NA_ZVEREJNENÚ_ZMLUVU") or "").strip())
        if kluc != ("", "") and kluc in videne:
            continue
        videne.add(kluc)
        data.append(r)
    if len(data) < 1000:
        raise RuntimeError(f"Zmluvy: podozrivo málo záznamov ({len(data)}).")
    teraz = datetime.now(timezone.utc)
    pred_rokom = teraz - timedelta(days=365)

    po_rokoch: dict[str, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0})
    dodavatelia: dict[str, dict] = {}
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
        if not ico or not ico.isdigit():
            bez_ico_suma += suma
            continue
        if ico == ICO_MESTA:
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
                "dodatok": str(r.get("DODATOK_K_EXISTUJÚCEJ_ZMLUVE")).lower() == "true",
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
            "najvacsie": najvacsie[:20],
        },
    }
    uloz("zmluvy-bratislava.json", vystup)


# --- Majetok mesta (pozemky) -------------------------------------------------

MAJETOK_ID = "8bd7889eaba647d4adcbc1e3516532cf"
# Katastrálne územia -> mestské časti (kód obce ŠÚ SR).
KU_MC = {
    "Staré Mesto": "528595", "Podunajské Biskupice": "529311", "Ružinov": "529320", "Nivy": "529320",
    "Trnávka": "529320", "Vrakuňa": "529338", "Nové Mesto": "529346", "Vinohrady": "529346",
    "Rača": "529354", "Vajnory": "529362", "Devínska Nová Ves": "529371", "Dúbravka": "529389",
    "Karlova Ves": "529397", "Devín": "529401", "Lamač": "529419", "Záhorská Bystrica": "529427",
    "Čunovo": "529435", "Jarovce": "529443", "Petržalka": "529460", "Rusovce": "529494",
}


def zber_majetok() -> None:
    item = polozka(MAJETOK_ID)
    data = riadky(item)
    if len(data) < 10000:
        raise RuntimeError(f"Majetok: podozrivo málo parciel ({len(data)}).")

    def nova():
        return {"parcely": 0, "vymera_m2": 0.0}

    spolu, druhy, casti, spravcovia, sprava = nova(), defaultdict(nova), defaultdict(nova), defaultdict(nova), defaultdict(nova)
    spoluvlastnictvo = 0
    nezaradene = set()
    for r in data:
        v = cislo(r.get("výmera__m2_")) or 0.0
        ku = (r.get("katastrálne_územie") or "").strip()
        mc = KU_MC.get(ku)
        if mc is None:
            nezaradene.add(ku)
        for ciel in (spolu, druhy[(r.get("druh_pozemku") or "Neuvedené").strip()],
                     casti[mc or "?"], spravcovia[(r.get("správca") or "Neuvedené").strip()],
                     sprava[(r.get("správa") or "neuvedené").strip()]):
            ciel["parcely"] += 1
            ciel["vymera_m2"] += v
        if (r.get("správcovský_vzťah") or "").strip() == "Spoluvlastník":
            spoluvlastnictvo += 1
    if nezaradene - {""}:
        raise RuntimeError(f"Majetok: neznáme katastrálne územia {sorted(nezaradene)}")

    def zoznam(d, n=None):
        x = sorted(({"nazov": k, "parcely": v["parcely"], "vymera_ha": round(v["vymera_m2"] / 1e4, 1)} for k, v in d.items()),
                   key=lambda i: -i["vymera_ha"])
        return x[:n] if n else x

    uloz("majetok-bratislava.json", {
        "zdroj": zdroj(item),
        "spolu": {"parcely": spolu["parcely"], "vymera_ha": round(spolu["vymera_m2"] / 1e4, 1), "spoluvlastnictvo": spoluvlastnictvo},
        "sprava": zoznam(sprava),
        "druhy": zoznam(druhy),
        "mestske_casti": [{"kod_obce": i["nazov"], "parcely": i["parcely"], "vymera_ha": i["vymera_ha"]} for i in zoznam(casti)],
        "spravcovia": zoznam(spravcovia, 12),
    })


# --- Doprava: cestujúci MHD a nehody ----------------------------------------

def zber_doprava_statistiky() -> None:
    cest = polozka("34a7ec013dcd4ba4a1bd6f7051e13a78")
    kvartaly: dict[str, dict[str, float]] = defaultdict(dict)
    for r in riadky(cest):
        q = re.sub(r"\D", "", str(r.get("KVARTAL") or ""))
        v = cislo(r.get("PREPRAVENE_OSOBY"))
        if q and v is not None:
            kvartaly[str(r["ROK"]).strip()][q] = v
    # Ročný súčet len za roky so všetkými štyrmi štvrťrokmi.
    rocne = {rok: sum(q.values()) for rok, q in sorted(kvartaly.items()) if len(q) == 4}

    nehody = {}
    for kluc, item_id in [("vsetky", "39d5a295afd24560bacd092e80531401"), ("so_zranenim", "b72dc2a2559745bdbc29a7a678b7a8e9")]:
        item = polozka(item_id)
        po_okresoch: dict[str, dict[str, float]] = defaultdict(dict)
        for r in riadky(item):
            v = cislo(r.get("Počet_nehôd"))
            if v is not None:
                po_okresoch[str(r["Okres"]).strip()][str(r["Rok"]).strip()] = v
        nehody[kluc] = {"zdroj": zdroj(item), "okresy": {o: dict(sorted(v.items())) for o, v in sorted(po_okresoch.items())}}
    if not rocne or not nehody["vsetky"]["okresy"]:
        raise RuntimeError("Doprava: prázdne dáta.")
    uloz("doprava-statistiky-bratislava.json", {
        "cestujuci": {"zdroj": zdroj(cest), "rocne": rocne,
                      "kvartaly": {r: dict(sorted(q.items())) for r, q in sorted(kvartaly.items())}},
        "nehody": nehody,
    })


# --- Spoločné: mestské časti ------------------------------------------------

def mapa_mc() -> dict[str, str]:
    """Normalizovaný názov mestskej časti -> kód obce (z dát o obyvateľstve)."""
    obyv = json.loads((DATA / "obyvatelstvo-bratislava.json").read_text(encoding="utf-8"))
    return {norm(c["nazov_kratky"]): c["kod"][-6:] for c in obyv["mestske_casti"]}


def norm(s: str) -> str:
    s = (s or "").replace("Bratislava", "").replace("-", " ").replace("–", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def oprav_kodovanie(s: str) -> str:
    """Niektoré texty na portáli sú cp1250 prečítané ako latin1 (napr. „Èunovo“)."""
    try:
        return s.encode("latin1").decode("cp1250") if re.search(r"[ÈèÒòÌìÝ]", s or "") else s
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def kod_mc(nazov: str, mc: dict[str, str]) -> str | None:
    n = norm(oprav_kodovanie(nazov))
    if n in mc:
        return mc[n]
    return KU_MC.get(oprav_kodovanie(nazov).strip())


# --- Školy a škôlky (oficiálne zoznamy mesta) -------------------------------

def zber_skoly() -> None:
    mc = mapa_mc()
    vystup = {"typy": {}}
    for kluc, item_id, pole_mc, pole_nazov in [
        ("zs", "f1aeacee4f5d47778cebe21be0cb18dd", "Mestská_časť", "Názov_zriadenia"),
        ("ms", "3cca7b5834cd479597db95ac562ba1dd", "mestska_cast", "nazov"),
    ]:
        item = polozka(item_id)
        po_mc: dict[str, int] = defaultdict(int)
        zriadovatel: dict[str, int] = defaultdict(int)
        nezaradene = []
        for r in riadky(item):
            kod = kod_mc(r.get(pole_mc) or "", mc)
            if not kod:
                nezaradene.append(r.get(pole_mc))
                continue
            po_mc[kod] += 1
            nazov = (r.get(pole_nazov) or "").lower()
            zriadovatel["súkromné" if "súkrom" in nazov else "cirkevné" if any(k in nazov for k in ("cirkev", "katolíc", "evanjel", "sv.", "svät")) else "verejné"] += 1
        if sum(po_mc.values()) < 50:
            raise RuntimeError(f"Školy {kluc}: podozrivo málo záznamov ({sum(po_mc.values())}), nezaradené: {nezaradene[:5]}")
        vystup["typy"][kluc] = {"zdroj": zdroj(item), "spolu": sum(po_mc.values()), "zriadovatel": dict(zriadovatel),
                                "mestske_casti": dict(sorted(po_mc.items())), "nezaradene": len(nezaradene)}
    uloz("skoly-bratislava.json", vystup)


# --- Prostredie: odpad, stromy, čierne skládky ------------------------------

def zber_prostredie() -> None:
    mc = mapa_mc()
    odpad = {}
    for kluc, item_id, pole, popis, jednotka in [
        ("na_obyvatela", "807a19f89a494ad98710ec1c1bf5a688", "KO_V_KG_NA_OBYVATELA", "Komunálny odpad na obyvateľa", "kg"),
        ("recyklacia", "561283d458334890810f6c8bd1a186ea", "RECYKLACIA_KO", "Miera recyklácie komunálneho odpadu", "%"),
        ("skladkovanie", "8afaff7c1d8340929ee23ee65e1bccdc", "SKLADKOVANIE_KO", "Miera skládkovania komunálneho odpadu", "%"),
    ]:
        item = polozka(item_id)
        roky = {str(r["ROK"]).strip(): cislo(r.get(pole)) for r in riadky(item) if cislo(r.get(pole)) is not None}
        odpad[kluc] = {"popis": popis, "jednotka": jednotka, "zdroj": zdroj(item), "roky": dict(sorted(roky.items()))}

    item = polozka("b000dfd7da3c4b339d1d6033ccdb7c60")
    stromy: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {"stromy": 0, "kry": 0}))
    for r in riadky(item):
        kod = kod_mc(r.get("KATASTRALNE_UZEMIE") or "", mc)
        rok = str(r.get("ROK")).strip()
        if kod:
            stromy[rok][kod]["stromy"] += cislo(r.get("POCET_STROMOV")) or 0
            stromy[rok][kod]["kry"] += cislo(r.get("POCET_KROV")) or 0
    vysadba = {"zdroj": zdroj(item), "roky": {rok: dict(sorted(v.items())) for rok, v in sorted(stromy.items())}}

    item = polozka("aa1785e567e742f5bdb05bf0ab1234a5")
    skladky = []
    for r in riadky(item):
        gps = (r.get("GPS_súradnice_skládky") or "").replace(",", " ").split()
        if len(gps) != 2:
            continue
        lon, lat = float(gps[0]), float(gps[1])
        if lat < lon:  # poistka, keby boli súradnice prehodené
            lat, lon = lon, lat
        skladky.append({"lat": round(lat, 5), "lon": round(lon, 5), "kod_obce": kod_mc(r.get("Katastrálne_územie") or "", mc)})
    if not odpad["na_obyvatela"]["roky"] or not skladky:
        raise RuntimeError("Prostredie: prázdne dáta.")
    uloz("prostredie-bratislava.json", {"odpad": odpad, "vysadba": vysadba,
                                         "cierne_skladky": {"zdroj": zdroj(item), "rok": "2025", "body": skladky}})


# --- Zdieľané bicykle Slovnaft BAjk -----------------------------------------

def zber_bajk() -> None:
    from shapely.geometry import Point, shape
    hranice = json.loads((DATA / "hranice-bratislava.geojson").read_text(encoding="utf-8"))
    casti = [(f["properties"]["kod_obce"], shape(f["geometry"])) for f in hranice["features"]]
    item = polozka("08643896d1b04f69a084f85c07677507")
    stanice = []
    for r in riadky(item):
        lat, lon = cislo(r.get("GPSlat")), cislo(r.get("GPSlon"))
        if lat is None or lon is None:
            continue
        p = Point(lon, lat)
        kod = next((k for k, g in casti if g.contains(p)), None)
        stanice.append({"nazov": (r.get("Názov") or "").strip(), "lat": round(lat, 5), "lon": round(lon, 5), "kod_obce": kod})
    if len(stanice) < 20:
        raise RuntimeError(f"BAjk: podozrivo málo staníc ({len(stanice)}).")
    uloz("bajk-bratislava.json", {"zdroj": zdroj(item), "stanice": sorted(stanice, key=lambda x: x["nazov"])})


def main() -> int:
    chyby = []
    for nazov, funkcia in [("rozpočet", zber_rozpocet), ("ovzdušie", zber_ovzdusie), ("zmluvy", zber_zmluvy), ("doprava", zber_doprava_statistiky), ("majetok", zber_majetok),
                           ("školy", zber_skoly), ("prostredie", zber_prostredie), ("bajk", zber_bajk)]:
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
