"""Mapové vrstvy z datasetov hlavného mesta (data.bratislava.sk).

Bezbariérové miesta, pitné fontány, športoviská, služby pre ľudí bez domova, veterinárne zariadenia,
vysadené stromy (od 2019) a starostlivosť o dreviny. Ak dataset nemá súradnice, poloha sa určí
z registra adries MV SR (číslo domu, inak stred ulice).

GDPR: nezverejňujeme mená referentov, darcov stromov, editorov záznamov ani kontakty osôb;
pri chovných zariadeniach len veterinárne ambulancie a kliniky (farmy môžu byť adresy fyzických osôb).

Výstupy:
  public/data/vrstvy-bratislava.json – body pre mapu (miesta)
  public/data/stromy-mesto.json      – vysadené a ošetrované stromy (načíta sa až po zapnutí)
  data/vrstvy-bratislava.json        – počty pre stránky a asistenta
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone

from pyproj import Transformer

from spolocne import url_vrstvy, DATA, VEREJNE, geokoder, mc_podla_polohy, s, spusti, zapis_ak_zmena

ITEM = "https://www.arcgis.com/sharing/rest/content/items/{}"
KATEGORIE = {"bezbarierove": "Bezbariérové miesta", "fontany": "Pitné fontány", "sportoviska": "Športoviská",
             "bezdomovci": "Pomoc ľuďom bez domova", "veterina": "Veterinárne ambulancie a kliniky"}
_jtsk = Transformer.from_crs("EPSG:5514", "EPSG:4326", always_xy=True)


def vrstva(item: str) -> str:
    return url_vrstvy(item)


def riadky(item: str, geometria: bool = False) -> list[dict]:
    url, vysl, offset = vrstva(item), [], 0
    while True:
        r = s.get(url + "/query", params={"where": "1=1", "outFields": "*", "returnGeometry": str(geometria).lower(), "outSR": 4326,
                                          "resultOffset": offset, "resultRecordCount": 2000, "f": "json"}, timeout=180).json()
        if "error" in r:
            raise RuntimeError(r["error"])
        f = r.get("features", [])
        for x in f:
            a = dict(x["attributes"])
            if geometria and x.get("geometry"):
                a["_lon"], a["_lat"] = x["geometry"].get("x"), x["geometry"].get("y")
            vysl.append(a)
        if len(f) < 2000 and not r.get("exceededTransferLimit"):
            return vysl
        offset += len(f)


def suradnice(x, y) -> tuple[float, float] | None:
    """X/Y v tabuľke: WGS84 (lon/lat) alebo S-JTSK (záporné metre)."""
    try:
        x, y = float(str(x).replace(",", ".")), float(str(y).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if abs(x) > 1000 or abs(y) > 1000:
        lon, lat = _jtsk.transform(-abs(x), -abs(y)) if abs(x) < abs(y) else _jtsk.transform(-abs(y), -abs(x))
        return lat, lon
    if 47 < x < 49 and 16 < y < 18:
        return x, y
    if 47 < y < 49 and 16 < x < 18:
        return y, x
    return None


def t(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def ano(v) -> bool:
    return t(v).lower() in ("áno", "ano", "1", "true", "yes", "x")


def plne_id(prefix: str) -> str:
    import json
    for p in json.loads((DATA / "katalog-bratislava.json").read_text(encoding="utf-8"))["datasety"]:
        if p["id"].startswith(prefix):
            return p["id"]
    raise RuntimeError(f"Dataset {prefix} nie je v inventári")


def main() -> int:
    najdi_mc = mc_podla_polohy()
    geo = geokoder()
    body, stromy, statistika, chyby = [], [], Counter(), []

    def pridaj(miesto, kat, nazov, det, ciel=None):
        ciel = body if ciel is None else ciel
        if miesto and najdi_mc(miesto[1], miesto[0]):
            ciel.append([round(miesto[0], 5), round(miesto[1], 5), kat, nazov, {k: v for k, v in det.items() if v not in (None, "", [], False)}])
            statistika[kat] += 1
        else:
            statistika[kat + "_bez_polohy"] += 1

    # 1. Bezbariérovosť (súradnice X, Y)
    try:
        rr = riadky(plne_id("ccaa77c5"))
        print("Bezbariérovosť ukážka:", {k: rr[0].get(k) for k in ("X", "Y", "druh", "poddruh", "adresa")})
        for r in rr:
            miesto = suradnice(r.get("X"), r.get("Y")) or (lambda g: g[:2] if g else None)(geo(r.get("mestská_časť"), t(r.get("adresa"))))
            info = [f"{n}: {t(r.get(k))}" for n, k in (("Pohyb", "pohyb_text"), ("WC", "wc_bezbariérové_text"), ("Aktivity", "aktivity_text"),
                                                     ("Vybavenie", "pohyb_špeciálne_vybavenie_text"), ("Zrak", "zrak_text"), ("Sluch", "sluch_text"),
                                                     ("Doprava", "doprava_text"), ("Iné", "iné_text")) if t(r.get(k))]
            pridaj(miesto, "bezbarierove", t(r.get("názov")), {"typ": " · ".join(x for x in (t(r.get("druh")), t(r.get("poddruh"))) if x),
                                                              "a": t(r.get("adresa")), "info": info, "w": t(r.get("web_link_1"))})
    except Exception as e:  # noqa: BLE001
        chyby.append(f"1. Bezbariérovosť (súradnice X, Y): {e}")
        print(f"CHYBA 1. Bezbariérovosť (súradnice X, Y): {e}")

    # 2. Pitné fontány (poloha z textu lokality alebo z adresy)
    try:
        rr = riadky(plne_id("226e7387"))
        print("Fontány ukážka:", rr[:2])
        for r in rr:
            text = " ".join(t(r.get(k)) for k in ("Lokalita", "Popis", "Poznámka"))
            m = re.search(r"(4[78][.,]\d{3,})\s*[,;\s]\s*(1[67][.,]\d{3,})", text)
            miesto = (float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))) if m else None
            if not miesto:
                g = geo(r.get("Mestská_časť"), t(r.get("Lokalita")))
                miesto = g[:2] if g else None
            foto = t(r.get("Fotografia"))
            pridaj(miesto, "fontany", t(r.get("Lokalita")) or "Pitná fontána", {"typ": t(r.get("Kategória")), "pop": t(r.get("Popis")),
                                                                                 "op": t(r.get("Správca")), "info": [t(r.get("Poznámka"))] if t(r.get("Poznámka")) else [],
                                                                                 "f": foto if foto.startswith("http") else None, "mc": t(r.get("Mestská_časť"))})
    except Exception as e:  # noqa: BLE001
        chyby.append(f"2. Pitné fontány (poloha z textu lokality alebo z adresy): {e}")
        print(f"CHYBA 2. Pitné fontány (poloha z textu lokality alebo z adresy): {e}")

    # 3. Športoviská (poloha z registra adries)
    try:
        presnost = Counter()
        for r in riadky(plne_id("ffc00f30")):
            g = geo(r.get("MESTSKA_CAST"), t(r.get("ULICA")), t(r.get("ORIENTACNE_CISLO")))
            presnost[g[2] if g else "nenájdené"] += 1
            pridaj(g[:2] if g else None, "sportoviska", t(r.get("OFICIALNY_NAZOV")) or t(r.get("SPORT")),
                   {"typ": t(r.get("SPORT")), "a": " ".join(x for x in (t(r.get("ULICA")), t(r.get("ORIENTACNE_CISLO"))) if x),
                    "info": [x for x in (t(r.get("OUTDOOR_INDOOR")), f"pre verejnosť: {t(r.get('DOSTUPNOST_PRE_VEREJNOST'))}" if t(r.get("DOSTUPNOST_PRE_VEREJNOST")) else "",
                                         f"spoplatnenie: {t(r.get('SPOPLATNENIE_PRE_VEREJNOST'))}" if t(r.get("SPOPLATNENIE_PRE_VEREJNOST")) else "") if x],
                    "pribl": g and g[2] == "ulica"})
        print("Športoviská – presnosť polohy:", dict(presnost))
    except Exception as e:  # noqa: BLE001
        chyby.append(f"3. Športoviská (poloha z registra adries): {e}")
        print(f"CHYBA 3. Športoviská (poloha z registra adries): {e}")

    # 4. Služby pre ľudí bez domova (Latitude/Longitude)
    try:
        for r in riadky(plne_id("5242099b")):
            miesto = suradnice(r.get("Latitude"), r.get("Longitude"))
            sluzby = [n for n, k in (("sociálno-právne poradenstvo", "Socialne_pravne_poradenstvo"), ("hygiena a ošatenie", "Hygiena_osatenie"),
                                     ("nocľah a ubytovanie", "Noclah_ubytovanie"), ("strava", "Strava"), ("zdravotné ošetrenie", "Zdravotne_osetrenie"),
                                     ("kontaktné centrum", "Kontaktne_centrum"), ("kultúra", "Kultura")) if ano(r.get(k))]
            pridaj(miesto, "bezdomovci", t(r.get("Nazov")), {"typ": ", ".join(sluzby) or t(r.get("Tagy")), "op": t(r.get("Poskytovatel")), "a": t(r.get("Adresa")),
                                                              "pop": t(r.get("Popis"))[:300], "h_text": t(r.get("Cas")), "tel": t(r.get("Telefon")), "w": t(r.get("Web"))})
    except Exception as e:  # noqa: BLE001
        chyby.append(f"4. Služby pre ľudí bez domova (Latitude/Longitude): {e}")
        print(f"CHYBA 4. Služby pre ľudí bez domova (Latitude/Longitude): {e}")

    # 5. Veterinárne zariadenia (len ambulancie a kliniky)
    try:
        rr = riadky(plne_id("48b41105"), geometria=True)
        print("Typy chovných a veterinárnych zariadení:", Counter(t(r.get("Typ_zariadenia_1")) for r in rr).most_common(12))
        for r in rr:
            typ = t(r.get("Typ_zariadenia_1"))
            if not re.search(r"veterin|klinik|ambulan|nemocnic|lekár", typ, re.I):
                continue
            pridaj((r.get("_lat"), r.get("_lon")) if r.get("_lat") else None, "veterina", t(r.get("Názov_zariadenia_1")), {"typ": typ, "a": t(r.get("Adresa_zariadenia_1"))})
    except Exception as e:  # noqa: BLE001
        chyby.append(f"5. Veterinárne zariadenia (len ambulancie a kliniky): {e}")
        print(f"CHYBA 5. Veterinárne zariadenia (len ambulancie a kliniky): {e}")

    # 6. Stromy: výsadba od 2019 (bez darcov) a starostlivosť o dreviny (bez referentov a dodávateľov)
    try:
        for r in riadky(plne_id("9d318577"), geometria=True):
            pridaj((r.get("_lat"), r.get("_lon")) if r.get("_lat") else None, "vysadba", t(r.get("drevina_sk")) or t(r.get("drevina_lat")),
                   {"lat": t(r.get("drevina_lat")), "rok": t(r.get("Vysadba_rok")) or t(r.get("obdobie")), "proj": t(r.get("projekt")), "ku": t(r.get("nazov_ku"))}, stromy)
        for r in riadky(plne_id("0ce440f8"), geometria=True):
            miesto = (r.get("_lat"), r.get("_lon")) if r.get("_lat") else suradnice(r.get("X"), r.get("Y"))
            vykony = [x for x in (t(r.get("POPIS_VYKONU_1")) or t(r.get("TYP_VYKONU_1")), t(r.get("POPIS_VYKONU_2")) or t(r.get("TYP_VYKONU_2")),
                                  t(r.get("POPIS_VYKONU_3")) or t(r.get("TYP_VYKONU_3"))) if x]
            pridaj(miesto, "starostlivost", t(r.get("Drevina_SK")) or t(r.get("Drevina_LAT")),
                   {"lat": t(r.get("Drevina_LAT")), "vykon": vykony, "ul": t(r.get("ULICA")), "ku": t(r.get("KU"))}, stromy)
    except Exception as e:  # noqa: BLE001
        chyby.append(f"6. Stromy: výsadba od 2019 (bez darcov) a starostlivosť o dreviny (bez referentov a dodávateľov): {e}")
        print(f"CHYBA 6. Stromy: výsadba od 2019 (bez darcov) a starostlivosť o dreviny (bez referentov a dodávateľov): {e}")

    if len(body) < 300:
        raise RuntimeError(f"Málo bodov ({len(body)}): {dict(statistika)}; chyby {chyby}")
    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zdroj = {"nazov": "Hlavné mesto SR Bratislava – data.bratislava.sk", "url": "https://data.bratislava.sk", "licencia": "CC BY 4.0"}
    zapis_ak_zmena(VEREJNE / "vrstvy-bratislava.json", {"zdroj": zdroj, "kategorie": KATEGORIE, "body": body, "aktualizovane": teraz}, kompaktne=True)
    zapis_ak_zmena(VEREJNE / "stromy-mesto.json", {"zdroj": zdroj, "kategorie": {"vysadba": "Vysadené stromy (od 2019)", "starostlivost": "Ošetrené dreviny"},
                                                   "body": stromy, "aktualizovane": teraz}, kompaktne=True)
    sporty = Counter(b[4].get("typ") for b in body if b[2] == "sportoviska")
    zapis_ak_zmena(DATA / "vrstvy-bratislava.json", {"zdroj": zdroj, "pocty": dict(statistika), "sporty": dict(sporty.most_common(25)),
                                                     "vysadba_po_rokoch": dict(sorted(Counter(str(b[4].get("rok") or "neuvedený") for b in stromy if b[2] == "vysadba").items())),
                                                     "aktualizovane": teraz})
    print("Vrstvy:", dict(statistika))
    return 0


if __name__ == "__main__":
    spusti(main, "Zber mapových vrstiev")
