"""Firmy vlastnené krajskými mestami – hospodárenie z účtovných závierok.

1. Kandidáti: zmluvní partneri a dodávatelia miest (CRZ, portály miest) s právnou formou a. s. / s. r. o. a názvom,
   ktorý odkazuje na mesto, + ručný zoznam (RUCNE).
2. Vlastníctvo: Register právnických osôb (api.statistics.sk/rpo) – jediný akcionár alebo spoločník je mesto (IČO
   mesta, prípadne vklad s názvom mesta). Mená fyzických osôb (štatutári, dozorná rada) nečítame ani neukladáme.
3. Hospodárenie: Register účtovných závierok – individuálne závierky podľa šablóny Úč POD (podnikatelia):
   čistý obrat, výnosy a náklady z hospodárskej činnosti, osobné náklady, odpisy, výsledok po zdanení,
   majetok, vlastné imanie, záväzky, bankové úvery (dlhodobé + bežné).

Výstup: data/mesta/firmy.json  {slug: [{ico, nazov, vlastnictvo, overenie, roky: {rok: {...}}}]}
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone

from spolocne import DATA, KOREN, s, spusti, zapis_ak_zmena
from zber_hospodarenie import OD_ROKU, ruz, sablona

CASOVY_LIMIT = 30 * 60  # po 30 min uložíme rozpracované a pokračujeme v ďalšom behu

RPO = "https://api.statistics.sk/rpo/v1"
MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))
KMENE = {"bratislava": r"bratislav", "kosice": r"košic|kosic", "presov": r"prešov|presov", "zilina": r"žilin|zilin", "banska-bystrica": r"bansk\w* bystric|banskobystr",
         "nitra": r"nitr", "trnava": r"trnav", "trencin": r"trenčí|trencin|trenčian"}
FORMA = re.compile(r"\ba\.\s?s\.|akciov|s\.\s?r\.\s?o|spol\.", re.I)
# a. s., pri ktorých RPO akcionára neuvádza (akcie na meno) – vlastníctvo mesta podľa výročných správ a webu mesta
RUCNE = {"kosice": ["31701914"], "banska-bystrica": ["36016411"]}
# ďalší kandidáti, ktorí nemusia byť medzi zmluvnými partnermi (vlastníctvo sa overí v RPO)
DOPLNKY = {"bratislava": ["00492736", "00681300"]}

# (kľúč, tabuľka, číslo riadku, stĺpec) – Úč POD: aktíva [brutto, korekcia, netto, netto minulé], pasíva a VZaS [bežné, minulé]
POD = [("obrat", "Výkaz ziskov a strát", 1, 0), ("vynosy", "Výkaz ziskov a strát", 2, 0), ("naklady", "Výkaz ziskov a strát", 10, 0),
       ("osobne_naklady", "Výkaz ziskov a strát", 15, 0), ("odpisy", "Výkaz ziskov a strát", 22, 0), ("vysledok", "Výkaz ziskov a strát", 61, 0),
       ("majetok", "Strana aktív", 1, 2), ("vlastne_imanie", "Strana pasív", 80, 0), ("zavazky", "Strana pasív", 101, 0),
       ("uvery_dlhodobe", "Strana pasív", 121, 0), ("uvery_bezne", "Strana pasív", 139, 0)]


def kandidati() -> dict[str, dict[str, str]]:
    """{slug: {ico: názov}} z uložených zmlúv a dodávateľov."""
    vysl: dict[str, dict[str, str]] = {m["slug"]: {} for m in MESTA}

    def pridaj(slug: str, ico: str | None, nazov: str | None) -> None:
        ico = re.sub(r"\D", "", str(ico or ""))
        if not (6 <= len(ico) <= 8) or not nazov or not FORMA.search(nazov):
            return
        if re.search(KMENE[slug], nazov, re.I) or re.search(r"\bmest", nazov, re.I):
            vysl[slug].setdefault(ico.zfill(8), nazov)

    for f in (DATA / "zmluvy-mesta").glob("20*.json"):
        for z in json.loads(f.read_text(encoding="utf-8")).values():
            pridaj(z["m"], z.get("ico"), z.get("p"))
    sam = DATA / "mesta" / "samosprava-kosice.json"
    if sam.exists():
        for fin in json.loads(sam.read_text(encoding="utf-8")).get("financie") or []:
            for d in fin["dodavatelia_posledne_3_roky"]:
                pridaj("kosice", d.get("ico"), d.get("nazov"))
    for subor in ("faktury-bratislava.json", "zmluvy-bratislava.json"):
        p = DATA / subor
        if p.exists():
            for ico, nazov in re.findall(r'"ico": ?"(\d{6,8})"[^{}]*?"(?:nazov|dodavatel|partner)": ?"([^"]+)"', p.read_text(encoding="utf-8")):
                pridaj("bratislava", ico, nazov)
            for nazov, ico in re.findall(r'"(?:nazov|dodavatel|partner)": ?"([^"]+)"[^{}]*?"ico": ?"(\d{6,8})"', p.read_text(encoding="utf-8")):
                pridaj("bratislava", ico, nazov)
    for slug, ica in [*RUCNE.items(), *DOPLNKY.items()]:
        for i in ica:
            vysl[slug].setdefault(i, "")
    return vysl


def vlastnik(ico: str, mesto: dict) -> tuple[str | None, str]:
    """('jediný' | 'podiel' | None, oficiálny názov firmy) podľa RPO – bez osobných údajov."""
    r = s.get(f"{RPO}/search", params={"identifier": ico}, timeout=60)
    time.sleep(0.4)
    if r.status_code != 200:
        return None, ""
    vysledky = r.json().get("results") or []
    if not vysledky:
        return None, ""
    e = s.get(f"{RPO}/entity/{vysledky[-1]['id']}", timeout=60).json()
    time.sleep(0.4)
    nazov = next((n.get("value") for n in reversed(e.get("fullNames") or []) if not n.get("validTo")), "") or ""
    if e.get("termination"):
        return None, nazov
    vlastnici = []
    for st in e.get("stakeholders") or []:
        typ = (st.get("stakeholderType") or {}).get("value", "")
        if st.get("validTo") or not re.search(r"akcionár|spoločník|zakladateľ", typ, re.I):
            continue
        if st.get("personName"):
            vlastnici.append("FO")  # fyzická osoba – len príznak, meno neukladáme
            continue
        idf = st.get("identifier") or next((x.get("value") for x in st.get("identifiers") or [] if x.get("value")), "")
        vlastnici.append(re.sub(r"\D", "", str(idf)).zfill(8) if idf else (st.get("fullName") or "").lower())
    for d in e.get("deposits") or []:
        if not d.get("validTo") and not d.get("personName"):
            vlastnici.append((d.get("fullName") or "").lower())
    mesto_nazvy = {mesto["ico"], f"mesto {mesto['nazov'].lower()}", "hlavné mesto slovenskej republiky bratislava"} if mesto["slug"] == "bratislava" else {mesto["ico"], f"mesto {mesto['nazov'].lower()}"}
    # mesto býva uvedené viackrát (spoločník podľa IČO aj vklady podľa názvu) – zjednotíme ho
    kluce = {"MESTO" if v in mesto_nazvy else v for v in vlastnici if v}
    if "MESTO" not in kluce:
        return None, nazov
    return ("jediný" if kluce == {"MESTO"} else "podiel"), nazov


def ukazovatele_pod(z: dict) -> dict:
    h: dict[str, float] = {}
    for vid in z.get("idUctovnychVykazov", []):
        v = ruz("uctovny-vykaz", id=vid)
        tab = (v.get("obsah") or {}).get("tabulky")
        if not tab or not v.get("idSablony"):
            continue
        sab = sablona(v["idSablony"])
        if sab["nazov"].strip() != "Úč POD":
            continue
        data = {t["nazov"]["sk"]: t["data"] for t in tab}
        for kluc, tabulka, riadok, stlpec in POD:
            st = sab["tabulky"].get(tabulka)
            if not st or tabulka not in data or riadok not in st["riadky"]:
                continue
            n = len(data[tabulka]) // max(1, len(st["riadky"]))
            try:
                h[kluc] = round(float(data[tabulka][st["riadky"][riadok] * n + stlpec] or 0))
            except (IndexError, ValueError):
                pass
    if "uvery_dlhodobe" in h or "uvery_bezne" in h:
        h["bankove_uvery"] = h.pop("uvery_dlhodobe", 0) + h.pop("uvery_bezne", 0)
    return h


def nove_roky(ico: str, videne: set[int]) -> tuple[dict, set[int]]:
    """Ukazovatele len zo závierok, ktoré sme ešte nespracovali (RÚZ je pomalý – každý dopyt ~1 s)."""
    ids = ruz("uctovne-jednotky", **{"zmenene-od": "2000-01-01", "ico": ico}).get("id", [])
    if not ids:
        return {}, videne
    uj = ruz("uctovna-jednotka", id=ids[0])
    roky: dict[str, tuple[str, dict]] = {}
    for zid in uj.get("idUctovnychZavierok", []):
        if zid in videne:
            continue
        z = ruz("uctovna-zavierka", id=zid)
        videne.add(zid)
        rok = (z.get("obdobieDo") or "")[:4]
        if z.get("konsolidovana") or not (z.get("obdobieDo") or "").endswith("-12") or not rok.isdigit() or int(rok) < OD_ROKU:
            continue
        u = ukazovatele_pod(z)
        if (u.get("vynosy") or u.get("majetok")) and (rok not in roky or (z.get("datumPoslednejUpravy") or "") >= roky[rok][0]):
            roky[rok] = (z.get("datumPoslednejUpravy") or "", u)
    return {r: u for r, (_, u) in roky.items()}, videne


def main() -> int:
    start = time.monotonic()
    stare_p = DATA / "mesta" / "firmy.json"
    stare = json.loads(stare_p.read_text(encoding="utf-8")) if stare_p.exists() else {}
    vystup: dict = {"zdroje": {"rpo": {"nazov": "Register právnických osôb (ŠÚ SR)", "url": "https://rpo.statistics.sk"},
                               "ruz": {"nazov": "Register účtovných závierok", "url": "https://www.registeruz.sk"}}, "mesta": {}}
    kand = kandidati()
    stare_firmy = {f"{slug}:{f['ico']}": f for slug, ff in (stare.get("mesta") or {}).items() for f in ff}
    # overené vlastníctvo si pamätáme 60 dní (RPO sa mení zriedka, beh by inak trval ~20 min)
    dnes = datetime.now(timezone.utc).date()
    overene: dict = {k: v for k, v in (stare.get("overene") or {}).items() if (dnes - datetime.fromisoformat(v["datum"]).date()).days < 60}
    vystup["overene"] = overene
    chyby = 0
    for m in MESTA:
        firmy = []
        print(f"{m['nazov']}: {len(kand[m['slug']])} kandidátov")
        for ico, nazov in sorted(kand[m["slug"]].items()):
            try:
                kluc = f"{m['slug']}:{ico}"
                if kluc in overene:
                    vl, oficialny = overene[kluc]["vl"], overene[kluc]["nazov"]
                else:
                    vl, oficialny = vlastnik(ico, m)
                    overene[kluc] = {"vl": vl, "nazov": oficialny, "datum": dnes.isoformat()}
                overenie = "RPO"
                if not vl and ico in RUCNE.get(m["slug"], []):
                    vl, overenie = "jediný", "výročná správa"
                if not vl:
                    continue
                stara = stare_firmy.get(f"{m['slug']}:{ico}", {})
                roky, videne = dict(stara.get("roky") or {}), set(stara.get("zavierky") or [])
                if time.monotonic() - start < CASOVY_LIMIT:
                    nove, videne = nove_roky(ico, videne)
                    roky.update(nove)
                firmy.append({"ico": ico, "nazov": oficialny or nazov, "vlastnictvo": vl, "overenie": overenie, "roky": dict(sorted(roky.items())), "zavierky": sorted(videne)})
                print(f"  {oficialny or nazov} ({ico}) – {vl}, rokov {len(roky)}")
            except Exception as e:  # noqa: BLE001
                chyby += 1
                print(f"::warning title=Firmy {m['nazov']} {ico}::{e}")
        if time.monotonic() - start >= CASOVY_LIMIT:
            print(f"::notice title=Firmy miest::časový limit – {m['nazov']} sa dokončí v ďalšom behu")
        if not firmy and m["slug"] in stare.get("mesta", {}):
            firmy = stare["mesta"][m["slug"]]
        vystup["mesta"][m["slug"]] = sorted(firmy, key=lambda f: -max([r.get("vynosy", 0) for r in f["roky"].values()] or [0]))
    if sum(len(v) for v in vystup["mesta"].values()) < 8:
        raise RuntimeError(f"Firmy miest: málo firiem ({chyby} chýb)")
    vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zapis_ak_zmena(DATA / "mesta" / "firmy.json", vystup)
    return 0


if __name__ == "__main__":
    spusti(main, "Firmy miest")
