"""Všeobecný import tabuliek z data.bratislava.sk do Katalógu dát (/data) a stav všetkých datasetov.

Vstup: data/katalog-bratislava.json (zber_katalog.py) a pravidlá v katalog_pravidla.py.
Výstupy:
  public/data/tabulky/<id>.json – údaje jednej tabuľky (stĺpce + riadky), načíta ich stránka /data/<id>
  data/katalog-stav.json        – každý dataset: stav (na webe / v katalógu / osobitný zber / vynechaný), kde a prečo
"""

from __future__ import annotations

import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from katalog_pravidla import (DATASETY_S_KONTAKTMI_ORGANIZACII, MAX_RIADKOV, NA_WEBE, OSOBITNE, RIADKY_PREC, STLPCE_KONTAKT, STLPCE_PREC,
                              STLPCE_VZDY_PREC, VYNECHANE)
from spolocne import DATA, VEREJNE, s, spusti, zapis_ak_zmena
from diakritika import hodnota as s_diakritikou, nazov_stlpca
import json

import os

from spolocne import KOREN

# Mesto: MESTO=kosice python scripts/zber_tabulky.py; pravidlá z katalog_pravidla.py platia len pre Bratislavu
MESTO = os.environ.get("MESTO", "bratislava")
BA = MESTO == "bratislava"
PORTAL = "https://data.bratislava.sk" if BA else next(m for m in json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8")) if m["slug"] == MESTO)["katalog"]["portal"]
CIEL = VEREJNE / ("tabulky" if BA else f"tabulky-{MESTO}")
STAV = DATA / ("katalog-stav.json" if BA else f"katalog-stav-{MESTO}.json")
# GDPR pre ostatné mestá (bez ručných pravidiel): osobné údaje kandidátov a mená fyzických osôb
STLPCE_OSOBNE = r"(^|_)(vek|povolan|zamestnan|bydlisk|trvaly|pobyt|narod|rodne|datum_nar|adresa_bydl|titul)"
# datasety, ktoré pri ostatných mestách vynechávame celé (názvy dokumentov môžu obsahovať mená ľudí)
VYNECHAT_MESTA = [(r"úradná tabuľa", "Názvy dokumentov na úradnej tabuli môžu obsahovať mená fyzických osôb (napr. doručovanie písomností) – nezverejňujeme.")]
STLPCE_OSOBY = r"(predkladatel|prijimatel|prijímateľ|ziadatel|žiadateľ|najomca|nájomca|meno|osoba|partner|dodavatel|dodávateľ|investor|stavebnik|stavebník|vlastnik|vlastník)"
PRAVNICKA = re.compile(r"s\.\s?r\.\s?o|spol\.|\ba\.\s?s\.|\bk\.\s?s\.|v\.\s?o\.\s?s|\bn\.\s?o\.|\bo\.\s?z\.|š\.\s?p\.|\bp\.\s?o\.|"
                       r"\b(mesto|mestsk\w*|obec|kraj|ministerstv\w*|úrad|univerzit\w*|škol\w*|nadácia|fond|cirkev|farnosť|zbor|zväz|združenie|spolok|klub|"
                       r"centrum|zariadenie|divadlo|múzeum|knižnica|spoločenstvo|družstvo|jednota|akadémia|organizácia|únia|gymnázium|tj|šk|fk|mfk|hk)\b", re.I)
MESACNE = {"bc6f1d93", "0de0dba7"}  # hodinové cyklosčítače 2014–2020 → súčty po mesiacoch


def kategoria(p: dict) -> str:
    for k in p.get("kategorie") or []:
        casti = [c for c in k.split("/") if c and c != "Categories"]
        if casti:
            return casti[-1].replace("_", " ")
    tagy = [t for t in p.get("tagy") or [] if t not in ("Bratislava 2050", "Bratislava", "data")]
    return tagy[0] if tagy else "Ostatné"


def hodnota(v, typ: str):
    if v is None:
        return None
    if typ == "Date" and isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, timezone.utc).strftime("%Y-%m-%d")
    if isinstance(v, str):
        t = v.strip()
        if re.fullmatch(r"-?\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|-?\d+(?:[.,]\d+)?", t) and not (len(t) > 1 and t[0] == "0" and t[1].isdigit()):
            t2 = re.sub(r"[  ]", "", t).replace(",", ".")
            try:
                f = float(t2)
                return int(f) if f.is_integer() and "." not in t2 else f
            except ValueError:
                return t
        return t
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def stiahni(url: str, krok: int = 2000) -> list[dict]:
    riadky, offset = [], 0
    while True:
        r = s.get(url + "/query", params={"where": "1=1", "outFields": "*", "returnGeometry": "false", "resultOffset": offset,
                                          "resultRecordCount": krok, "f": "json"}, timeout=180).json()
        if "error" in r:
            raise RuntimeError(r["error"].get("message"))
        davka = [f["attributes"] for f in r.get("features", [])]
        riadky += davka
        if len(davka) < krok and not r.get("exceededTransferLimit"):
            return riadky
        offset += len(davka)


def pekne(alias: str, meno: str) -> str:
    t = (alias or meno or "").replace("___", " – ").replace("__", " ").replace("_", " ").strip()
    t = re.sub(r"^F(\d)", r"\1", t)
    t = t[:1].upper() + t[1:].lower() if t.isupper() else t
    return nazov_stlpca(t)


def importuj(p: dict) -> dict:
    kid = p["id"][:8]
    v = p["vrstvy"][0]
    polia = [(n, typ, alias) for n, typ, alias in v["polia"] if not re.match(STLPCE_VZDY_PREC, n, re.I) and typ not in ("OID", "Geometry", "GlobalID")]
    prec = set(STLPCE_PREC.get(kid, []))
    if kid not in DATASETY_S_KONTAKTMI_ORGANIZACII:
        prec |= {n for n, _, _ in polia if re.search(STLPCE_KONTAKT, n, re.I)}
    if not BA:
        prec |= {n for n, _, a in polia if re.search(STLPCE_OSOBNE, f"{n}|{a or ''}", re.I)}
    polia = [x for x in polia if x[0] not in prec]
    # kandidáti vo voľbách: meno a strana sú verejné (ostatné osobné údaje sú preč vyššie)
    # kandidáti, poslanci a členovia orgánov mesta: meno a funkcia sú verejné (ostatné osobné údaje sú preč vyššie)
    osoby = [] if BA or re.search(r"kandid|poslan|komisi|mestská rada|zastupiteľ", p.get("nazov") or "", re.I) else [n for n, t, a in polia if t == "String" and re.search(STLPCE_OSOBY, f"{n}|{a or ''}", re.I)
                                                                                  and not re.search(r"ulica|adres|obec|mesto|psc|cislo|číslo|krajina|ico|dic|forma|projekt|schema|popis", n, re.I)]
    url = f"{p['sluzba']}/{v['id']}"
    riadky = stiahni(url)
    vynechane_riadky = 0
    if not BA:
        # prieskumy: voľné textové odpovede obyvateľov nezverejňujeme (len kódované odpovede a znenia otázok)
        if re.search(r"prieskum", p.get("nazov") or "", re.I):
            volne = []
            for n, t, _ in polia:
                hod = [str(r.get(n)) for r in riadky[:400] if r.get(n) not in (None, "")]
                if t == "String" and hod and sum(len(h) for h in hod) / len(hod) > 25 and not re.search(r"znenie|otazk|text_odpovede", n, re.I):
                    volne.append(n)
            prec |= set(volne)
            polia = [x for x in polia if x[0] not in prec]
        # žiadatelia – fyzické osoby: meno nahradiť, adresu a identifikátory vypustiť
        for pf in [n for n, _, _ in polia if re.search(r"pravna_forma", n, re.I)]:
            predpona = pf[: pf.lower().index("pravna_forma")]
            rovnake = [n for n, _, _ in polia if predpona and n.startswith(predpona) and n != pf]
            for r in riadky:
                if re.search(r"fyzick|slobodn\w* umel|samostatne zárob", str(r.get(pf) or ""), re.I):
                    for n in rovnake:
                        r[n] = "fyzická osoba" if re.search(r"nazov|meno", n, re.I) else None
                    vynechane_riadky += 1
    # kde dataset uvádza právnu formu, rozhoduje len ona (inak by sa nahradili aj názvy združení bez „o. z.“)
    predpony_pf = [n[: n.lower().index("pravna_forma")] for n, _, _ in polia if re.search(r"pravna_forma", n, re.I)]
    osoby = [n for n in osoby if not any(pp and n.startswith(pp) for pp in predpony_pf)]
    for n in osoby:  # meno fyzickej osoby → „fyzická osoba“ (súčty ostanú)
        for r in riadky:
            v = str(r.get(n) or "").strip()
            if v and not PRAVNICKA.search(v) and re.match(r"^(?:[A-Za-z]{2,6}\.\s*)*[A-ZÁČĎÉÍĽĹŇÓÔŔŠŤÚÝŽ][a-záäčďéíľĺňóôŕšťúýž]+(?:[ -][A-ZÁČĎÉÍĽĹŇÓÔŔŠŤÚÝŽ][a-záäčďéíľĺňóôŕšťúýž]+){1,3}(?:,.*)?$", v):
                r[n] = "fyzická osoba"
                vynechane_riadky += 1
    if BA and kid in RIADKY_PREC:
        stlpec, pravidlo = RIADKY_PREC[kid]
        povodne = len(riadky)
        if pravidlo == "ico":
            riadky = [r for r in riadky if len(re.sub(r"\D", "", str(r.get(stlpec) or ""))) >= 6]
        else:
            fo = re.compile(r"^(?:[A-Za-z]{2,5}\.\s*)*[A-ZÁČĎÉÍĽĹŇÓÔŔŠŤÚÝŽ][a-záäčďéíľĺňóôŕšťúýž]+ [A-ZÁČĎÉÍĽĹŇÓÔŔŠŤÚÝŽ][a-záäčďéíľĺňóôŕšťúýž]+(ová)?\s*(,|-|$)")
            riadky = [r for r in riadky if not fo.match(str(r.get(stlpec) or "").strip())]
        vynechane_riadky = povodne - len(riadky)
    if kid in MESACNE:
        cas = next(n for n, t, _ in polia if t == "Date" or "čas" in n.lower() or "dátum" in n.lower())
        cisla = [n for n, t, _ in polia if n != cas and t in ("Integer", "SmallInteger", "Double")]
        sucet: dict[str, dict] = defaultdict(lambda: defaultdict(int))
        for r in riadky:
            m = str(hodnota(r.get(cas), "Date"))[:7]
            for n in cisla:
                sucet[m][n] += int(r.get(n) or 0)
        stlpce = [{"k": "mesiac", "n": "Mesiac", "t": "String"}] + [{"k": n, "n": pekne(a, n), "t": "Integer"} for n, _, a in polia if n in cisla]
        data = [[m] + [sucet[m][n] for n in cisla] for m in sorted(sucet)]
    else:
        stlpce = [{"k": n, "n": pekne(a, n), "t": t} for n, t, a in polia]
        data = [[s_diakritikou(hodnota(r.get(n), t)) for n, t, _ in polia] for r in riadky]
        # prázdne stĺpce preč
        plne = [i for i in range(len(stlpce)) if any(row[i] not in (None, "") for row in data)]
        stlpce = [stlpce[i] for i in plne]
        data = [[row[i] for i in plne] for row in data]
    vystup = {"id": p["id"], "nazov": p["nazov"], "popis": p.get("popis"), "kategoria": kategoria(p), "licencia": p.get("licencia") or "CC BY 4.0",
              "zdroj": f"{PORTAL}/datasets/{p['id']}", "upravene": p.get("upravene"), "mesacne": kid in MESACNE,
              "odstranene_stlpce": sorted(prec), "vynechane_riadky": vynechane_riadky, "stlpce": stlpce, "riadky": data}
    CIEL.mkdir(parents=True, exist_ok=True)
    zapis_ak_zmena(CIEL / f"{p['id']}.json", vystup, kompaktne=True, ignoruj=("upravene",))
    return {"riadkov": len(data), "stlpcov": len(stlpce)}


def main() -> int:
    katalog = json.loads((DATA / f"katalog-{MESTO}.json").read_text(encoding="utf-8"))
    unikatne = {}
    for p in katalog["datasety"]:
        unikatne.setdefault(p["id"], p)
    stav, na_import = [], []
    for p in unikatne.values():
        kid = p["id"][:8]
        zaznam = {"id": p["id"], "nazov": p["nazov"], "kategoria": kategoria(p), "upravene": p.get("upravene"),
                  "riadkov": sum((v.get("pocet") or 0) for v in p.get("vrstvy", [])) or None}
        if BA and kid in NA_WEBE:
            zaznam |= {"stav": "na_webe", "kde": NA_WEBE[kid][0], "pozn": NA_WEBE[kid][1]}
        elif BA and kid in OSOBITNE and kid not in MESACNE:
            zaznam |= {"stav": "osobitne", "kde": OSOBITNE[kid][0], "pozn": OSOBITNE[kid][1]}
        elif BA and kid in VYNECHANE:
            zaznam |= {"stav": "vynechane", "dovod": VYNECHANE[kid]}
        elif not BA and any(re.search(v, p.get("nazov") or "", re.I) for v, _ in VYNECHAT_MESTA):
            zaznam |= {"stav": "vynechane", "dovod": next(d for v, d in VYNECHAT_MESTA if re.search(v, p.get("nazov") or "", re.I))}
        elif not p.get("vrstvy"):
            zaznam |= {"stav": "vynechane", "dovod": f"Typ „{p.get('typ')}“ bez tabuľkovej služby – nedá sa načítať automaticky." + (f" ({p.get('chyba')})" if p.get("chyba") else "")}
        elif not (p["vrstvy"][0].get("pocet") or 0):
            zaznam |= {"stav": "vynechane", "dovod": "Dataset je prázdny (0 záznamov)."}
        elif p["vrstvy"][0].get("geometria") and kid not in MESACNE:
            zaznam |= {"stav": "vynechane", "dovod": "Mapová vrstva bez pravidla na spracovanie – doplniť do osobitného zberu."}
        elif (p["vrstvy"][0].get("pocet") or 0) > MAX_RIADKOV and kid not in MESACNE:
            zaznam |= {"stav": "vynechane", "dovod": f"Príliš veľký na všeobecný import ({p['vrstvy'][0]['pocet']} riadkov) – vyžaduje osobitné spracovanie."}
        else:
            zaznam |= {"stav": "katalog", "kde": f"/{MESTO}/katalog/{p['id']}"}
            na_import.append(p)
        stav.append(zaznam)

    def bezpecne(p):
        try:
            return p["id"], importuj(p), None
        except Exception as e:  # noqa: BLE001
            return p["id"], None, str(e)[:200]

    with ThreadPoolExecutor(6) as ex:
        vysledky = {i: (r, e) for i, r, e in ex.map(bezpecne, na_import)}
    chyby = 0
    for z in stav:
        if z["id"] in vysledky:
            r, e = vysledky[z["id"]]
            if e:
                chyby += 1
                z |= {"stav": "vynechane", "dovod": f"Chyba pri načítaní zo zdroja: {e}", "kde": None}
            else:
                z |= r
    # datasety, ktoré sú len v národnom katalógu (data.slovensko.sk), nie na portáli mesta
    if BA:
      stav.append({"id": "narodny-katalog-papsport", "nazov": "papsport plochy all fin", "kategoria": "Ostatné", "stav": "vynechane",
                 "dovod": "Pracovný súbor bez popisu a dokumentácie, uvedený len v národnom katalógu data.slovensko.sk – na portáli mesta nie je."})
    stav.sort(key=lambda z: (z["kategoria"], (z["nazov"] or "").lower()))
    pocty: dict[str, int] = defaultdict(int)
    for z in stav:
        pocty[z["stav"]] += 1
    zapis_ak_zmena(STAV, {"zdroj": PORTAL, "pocty": dict(pocty), "datasety": stav,
                                                "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")}, ignoruj=("aktualizovane",))
    print(f"Stav: {dict(pocty)}; chyby pri importe: {chyby}")
    if chyby > len(na_import) * 0.2:
        raise RuntimeError(f"Priveľa chýb pri importe ({chyby})")
    return 0


if __name__ == "__main__":
    spusti(main, "Import tabuliek")
