"""Čo sa stavia: posudzovanie vplyvov na životné prostredie (EIA/SEA) v Bratislave.

Zdroj: Enviroportál MŽP SR / SAŽP – Centrálny informačný systém EIA/SEA, verejné API
https://www.enviroportal.sk/api/eia_projects (zoznam zoradený podľa poslednej zmeny) a
https://www.enviroportal.sk/api/eia_projects/<seoId> (detail).

API sa nedá filtrovať, preto zber prejde zoznam od najnovšej zmeny a zastaví sa pri
zámeroch, ktoré sa odvtedy nezmenili. Detail sa sťahuje len pre zámery v Bratislave.

Polohu odhadneme podľa ulice spomenutej v názve alebo účele zámeru (register adries MV SR);
ak žiadna nie je, použije sa stred mestskej časti.

GDPR: navrhovateľa zverejňujeme len ak ide o právnickú osobu alebo inštitúciu (podľa
právnej formy v názve); fyzické osoby a živnostníci sa skryjú. Adresy navrhovateľov
ani spracovateľov nezverejňujeme.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta
from html import unescape

from spolocne import DATA, KOREN, VEREJNE, adresy_mv, bez_diakritiky, hranice, norm_mc, norm_ulica, s, spusti, zapis_ak_zmena

API = "https://www.enviroportal.sk/api/eia_projects"
WEB = "https://www.enviroportal.sk/eia/detail/"
ULOZISKO = DATA / "eia-bratislava.json"
# ostatné krajské mestá (src/mesta.json) – samostatné úložisko, poloha = stred mesta
ULOZISKO_MESTA = DATA / "eia-mesta.json"
DALSIE_MESTA = [m for m in json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8")) if m["slug"] != "bratislava"]
NA_STRANU = 100

PRAVNA_FORMA = re.compile(
    r"spol\.\s?s\s?r\.\s?o|s\.\s?r\.\s?o|spol\.|\ba\.\s?s\.|\bk\.\s?s\.|v\.\s?o\.\s?s|\bn\.\s?o\.|\bo\.\s?z\.|š\.\s?p\.|\bp\.\s?o\.|\bse\b|\b(?:gmbh|ltd|inc|kft|"
    r"mesto|mestsk\w*|obec|kraj|samosprávny|ministerstvo|úrad|univerzita|ústav|nadácia|fond|podnik|agentúra|správa|"
    r"železnice|letisko|nemocnica|spoločnosť|družstvo|zväz|združenie)\b", re.I)

KATEGORIE = [
    ("plan", r"územn\w* plán|koncepci|stratégi|program\b|plán udržateľnej|generel|zmeny a doplnky|^zad\b"),
    ("odpady", r"odpad|zhodnoc|recykl|skládk|kompost|drvi|triedi"),
    ("doprava", r"\bcest|diaľnic|rýchlostn|\bmost\b|\bmost[auy]\b|želez|\btrať|\btrate\b|električ|trolejb|radiál|križovat|parkovac\w* dom|parking|letisk|\bprístav(?!b)|chodník|cyklo|terminál"),
    ("energia", r"fotovolt|energ|tepl[áoé]|teplár|horúcovod|teplovod|plynov|kotol|kogener|transformov|vedenie|batéri|vodík"),
    ("priemysel", r"hal[ay]\b|sklad|logist|výrob|priemysel|areál\w* závod|čerpacia stanica|chemick|prevádzk|autoservis|lakovn"),
    ("byvanie", r"byt|obytn|rezid|polyfunk|bývan|rodinn\w* dom|apartm|vil[ay]\b|mestsk\w* štvrť|ubytovac|hotel|zóna|kampus"),
    ("voda", r"vod[ay]\b|vodovod|kanaliz|čistiar|protipovodň|studň|retenč|dunaj|potok"),
    ("obcianska", r"škol|nemocnic|šport|štadión|kúpal|obchod|nákupn|retail|centrum|admin|kancel|office|tower|veža"),
]
KATEGORIE_RE = [(k, re.compile(v, re.I)) for k, v in KATEGORIE]

# Stav, ktorým posudzovanie skončilo (rozhodnutie „posudzovať“ naopak znamená, že pokračuje)
UKONCENE = re.compile(r"záverečné stanovisko|rozhodnutie zo zisťovacieho|rozhodnutie vo veci|neposudzovať|iný dôvod ukončenia|ukončen|schválen|stiahnut|zastaven", re.I)
AKTIVNE_ROKY = 3  # zámer bez pohybu dlhšie ako 3 roky už nepovažujeme za prebiehajúci
VERZIA_POLOH = 2
# Názvy ulíc, ktoré sú zároveň bežné slová alebo časť názvu mestskej časti – podľa nich polohu neurčujeme
VSEOBECNE_ULICE = {"hlavna", "podnikova", "zeleznicna", "priemyselna", "obchodna", "sportova", "skolska", "polna", "kratka", "stanicna",
                   "nova", "stara", "dlha", "zahradna", "lesna", "parkova", "cintorinska", "kostolna", "namestie", "dunajska", "vodarenska"}
LEN_SEA = re.compile(r"časť SEA", re.I)


def ciste(t: str | None) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def je_bratislava(z: dict) -> bool:
    return (z.get("okres") or "").startswith("Bratislava") or (z.get("obec") or "").startswith("Bratislava")


def ine_mesto(z: dict) -> dict | None:
    """Zámer v inom krajskom meste – podľa obce („Košice - Juh“, „Žilina“), nie podľa okresu (ten zahŕňa aj obce okolo)."""
    obec = re.sub(r"\s+", " ", (z.get("obec") or "")).strip()
    for m in DALSIE_MESTA:
        if obec == m["nazov"] or obec.startswith(m["nazov"] + " -") or obec.startswith(m["nazov"] + "-"):
            return m
    return None


def mestske_casti(z: dict) -> list[str]:
    """„Bratislava - Petržalka“, viac častí v detaile („dotknutaObec“), inak celé mesto."""
    vysledok = []
    for t in re.split(r"[;,\n]| a (?=Bratislava)", (z.get("obec") or "") + ";" + ciste(z.get("dotknutaObec"))):
        t = re.sub(r"\(okres:.*?\)", "", t).strip(" -")
        mc = norm_mc(t)
        if mc and mc not in vysledok:
            vysledok.append(mc)
    return vysledok


def navrhovatel(n: dict | None) -> str | None:
    """Len právnické osoby a inštitúcie; názov bez adresy."""
    if not n or not n.get("name"):
        return None
    meno = ciste(n["name"])
    m = PRAVNA_FORMA.search(meno)
    if not m:
        return None
    # odrež adresu: za právnou formou („…, a. s., Legionárska 10“) alebo pri inštitúcii za prvou čiarkou
    if re.match(r"(?:s\.|spol|a\.|k\.|v\.|n\.|o\.|š\.|p\.|se\b|gmbh|ltd|inc|kft)", m.group(0), re.I):
        koniec = m.end() + (1 if meno[m.end():m.end() + 1] == "." else 0)
        meno = meno[:koniec]
    else:
        meno = meno.split(",")[0]
    return meno.strip(" ,")[:120]


def kategoria(nazov: str, ucel: str, sea: bool) -> str:
    if sea:
        return "plan"
    for k, r in KATEGORIE_RE:
        if r.search(nazov):
            return k
    for k, r in KATEGORIE_RE:
        if r.search(ucel[:400]):
            return k
    return "ine"


def datumy(det: dict) -> tuple[str | None, str | None]:
    """Prvý a posledný dátum dokumentu („03.06. 2026“)."""
    vsetky = []
    for krok in ((det.get("dokumenty") or {}).get("data") or []):
        for skupina in krok.get("items") or []:
            for d in skupina.get("items") or []:
                m = re.match(r"(\d{1,2})\.(\d{1,2})\.\s*(\d{4})", d.get("date") or "")
                if m:
                    vsetky.append(f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}")
    return (min(vsetky), max(vsetky)) if vsetky else (None, None)


def kroky(det: dict) -> list[str]:
    return [k.get("step") for k in ((det.get("dokumenty") or {}).get("data") or []) if k.get("step")]


def zaznam(det: dict) -> dict:
    nazov = ciste(det.get("name"))
    ucel = ciste(det.get("ucel"))
    sea = bool(LEN_SEA.search(det.get("zbierka") or ""))
    prvy, posledny = datumy(det)
    return {
        "id": str(det["id"]),
        "seo": det["seoId"],
        "nazov": nazov,
        "stav": ciste(det.get("stav")),
        "proces": ciste(det.get("proces")),
        "typ": "SEA" if sea else "EIA",
        "kat": kategoria(nazov, ucel, sea),
        "ucel": ucel[:700] + ("…" if len(ucel) > 700 else ""),
        "cinnosti": [ciste(c.get("num")) for c in (det.get("cinnosti") or []) if c.get("num")],
        "navrhovatel": navrhovatel(det.get("navrhovatel")),
        "ico": (det.get("navrhovatel") or {}).get("ico") if navrhovatel(det.get("navrhovatel")) else None,
        "mc": mestske_casti(det),
        "povoluje": ciste(det.get("povolujuciOrgan"))[:160] or None,
        "kroky": kroky(det),
        "od": prvy,
        "posledny_dokument": posledny,
        "zmena": (det.get("datumPoslednejZmeny") or "")[:10],
    }


def odvod(z: dict) -> dict:
    """Odvodené polia – prepočítajú sa pri každom behu (aj pre staré záznamy)."""
    z["kat"] = kategoria(z["nazov"], z.get("ucel") or "", z.get("typ") == "SEA")
    hranica = (date.today() - timedelta(days=365 * AKTIVNE_ROKY)).isoformat()
    z["ukoncene"] = bool(UKONCENE.search(z.get("stav") or "")) or (z.get("zmena") or "") < hranica
    return z


def zoznam_zmien(od: str | None) -> tuple[list[dict], list[dict]]:
    """Položky zoznamu zmenené od dátumu `od` (celý zoznam, ak od=None): (Bratislava, ostatné krajské mestá)."""
    ba, ine, strana = [], [], 1
    while True:
        r = s.get(API, params={"page": strana, "itemsPerPage": NA_STRANU}, headers={"Accept": "application/json"}, timeout=120)
        r.raise_for_status()
        j = r.json()
        polozky = j.get("data") or []
        if not polozky:
            break
        for z in polozky:
            if je_bratislava(z):
                ba.append(z)
            elif ine_mesto(z):
                ine.append(z)
        posledna = min((z.get("datumPoslednejZmeny") or "9999")[:10] for z in polozky)
        if od and posledna < od:
            break
        if strana >= int((j.get("meta") or {}).get("last_page") or strana):
            break
        strana += 1
        time.sleep(0.4)
    print(f"Zoznam: {strana} strán, {len(ba)} zámerov v Bratislave, {len(ine)} v ostatných krajských mestách")
    return ba, ine


def polohy(zamery: list[dict], stare: dict) -> None:
    """Doplní lat/lon (+ presnosť) podľa ulice v názve/účele, inak stred MČ."""
    treba = [z for z in zamery if "lat" not in z or z.get("_text") != stare.get(z["id"], {}).get("_text") or z.get("_poloha") != VERZIA_POLOH]
    if not treba:
        return
    stredy = {nazov: (g.representative_point().y, g.representative_point().x) for _, nazov, g in hranice()}
    ulice: dict[str, dict[str, list]] = {}
    mc_slova = {w for nazov in stredy for w in norm_ulica(nazov).split()}
    try:
        for a in adresy_mv():
            u = norm_ulica(a["ulica"])
            if len(u) >= 5 and u not in VSEOBECNE_ULICE and u not in mc_slova:
                ulice.setdefault(a["mc"], {}).setdefault(u, []).append((a["lat"], a["lon"]))
    except Exception as e:  # noqa: BLE001 – bez registra adries aspoň stred mestskej časti
        print("Register adries nedostupný:", e)
    vzory = {mc: sorted(((u, re.compile(r"\b" + re.escape(u) + r"\b")) for u in us), key=lambda x: -len(x[0])) for mc, us in ulice.items()}
    for z in treba:
        text = norm_ulica(z["nazov"] + " " + z["ucel"])
        z["_poloha"] = VERZIA_POLOH
        for k in ("lat", "lon", "presnost", "ulica"):
            z.pop(k, None)
        for mc in z["mc"]:
            for u, vzor in vzory.get(mc, []):
                if vzor.search(text):
                    body = ulice[mc][u]
                    z["lat"] = round(sum(b[0] for b in body) / len(body), 5)
                    z["lon"] = round(sum(b[1] for b in body) / len(body), 5)
                    z["presnost"] = "ulica"
                    z["ulica"] = u
                    break
            if "lat" in z:
                break
        if "lat" not in z and len(z["mc"]) == 1 and z["mc"][0] in stredy:
            z["lat"], z["lon"] = (round(x, 5) for x in stredy[z["mc"][0]])
            z["presnost"] = "mc"


def verejny(z: dict) -> dict:
    """Záznam pre web – bez pomocných polí; pri ukončených kratší popis (menší súbor)."""
    v = {k: x for k, x in z.items() if not k.startswith("_") and k not in ("cinnosti", "ico", "povoluje", "kroky")}
    if z["ukoncene"] and len(v["ucel"]) > 320:
        v["ucel"] = v["ucel"][:320].rsplit(" ", 1)[0] + "…"
    return v


def main() -> int:
    stare = {}
    od = None
    if ULOZISKO.exists():
        ulozene = json.loads(ULOZISKO.read_text(encoding="utf-8"))
        stare = {z["id"]: z for z in ulozene["zamery"]}
        # rezerva 3 dni – zoznam sa zoraďuje podľa času poslednej zmeny
        od = (date.fromisoformat(ulozene["posledna_zmena"]) - timedelta(days=3)).isoformat()
    stare_m, od_m = {}, None
    if ULOZISKO_MESTA.exists():
        ul = json.loads(ULOZISKO_MESTA.read_text(encoding="utf-8"))
        stare_m = {z["id"]: z for z in ul["zamery"]}
        od_m = (date.fromisoformat(ul["posledna_zmena"]) - timedelta(days=3)).isoformat()
    zmenene, zmenene_m = zoznam_zmien(min(od, od_m) if od and od_m else None)
    if od:
        zmenene = [z for z in zmenene if (z.get("datumPoslednejZmeny") or "")[:10] >= od]
    nove_m = dict(stare_m)
    for i, z in enumerate(zmenene_m):
        zmena = (z.get("datumPoslednejZmeny") or "")[:10]
        if z["id"] in stare_m and stare_m[z["id"]]["zmena"] == zmena:
            continue
        r = s.get(f"{API}/{z['seoId']}", headers={"Accept": "application/json"}, timeout=120)
        if r.status_code == 404:
            continue
        r.raise_for_status()
        det = r.json()
        det = det.get("data", det)
        m = ine_mesto(det) or ine_mesto(z)
        if not m:
            continue
        zaz = zaznam(det)
        zaz["mesto"] = m["slug"]
        obec = re.sub(r"\s+", " ", det.get("obec") or "")
        zaz["mc"] = [re.sub(r"^.*?-\s*(mestská časť\s*)?", "", obec).strip()] if obec != m["nazov"] and "-" in obec else []
        zaz["lat"], zaz["lon"], zaz["presnost"] = m["stred"][0], m["stred"][1], "mesto"
        nove_m[zaz["id"]] = zaz
        if i % 50 == 0:
            print(f"  detail (mestá) {i + 1}/{len(zmenene_m)}")
        time.sleep(0.3)
    zamery_m = sorted((odvod(z) for z in nove_m.values()), key=lambda z: (z["zmena"], z["id"]), reverse=True)
    if zamery_m:
        zapis_ak_zmena(ULOZISKO_MESTA, {"aktualizovane": datetime.now().isoformat(timespec="seconds"),
                                        "posledna_zmena": max(z["zmena"] for z in zamery_m if z["zmena"]), "zamery": zamery_m}, kompaktne=True)
        for m in DALSIE_MESTA:
            vm = [verejny(z) for z in zamery_m if z["mesto"] == m["slug"]]
            zapis_ak_zmena(VEREJNE / "mesta" / f"eia-{m['slug']}.json", {
                "aktualizovane": datetime.now().isoformat(timespec="seconds"), "web": WEB, "zamery": vm,
                "zdroj": {"nazov": "Enviroportál MŽP SR / SAŽP – Informačný systém EIA/SEA", "url": "https://www.enviroportal.sk/eia"}}, kompaktne=True)
            print(f"EIA {m['nazov']}: {len(vm)} zámerov, aktívnych {sum(not z['ukoncene'] for z in vm)}")

    nove = dict(stare)
    for i, z in enumerate(zmenene):
        zmena = (z.get("datumPoslednejZmeny") or "")[:10]
        if z["id"] in stare and stare[z["id"]]["zmena"] == zmena and "kroky" in stare[z["id"]]:
            continue
        r = s.get(f"{API}/{z['seoId']}", headers={"Accept": "application/json"}, timeout=120)
        if r.status_code == 404:
            continue
        r.raise_for_status()
        det = r.json()
        det = det.get("data", det)
        zaz = zaznam(det)
        zaz["_text"] = zaz["nazov"] + "|" + zaz["ucel"][:200] + "|" + ",".join(zaz["mc"])
        if z["id"] in stare:
            for k in ("lat", "lon", "presnost", "ulica", "_poloha"):
                if k in stare[z["id"]] and stare[z["id"]].get("_text") == zaz["_text"]:
                    zaz[k] = stare[z["id"]][k]
        nove[zaz["id"]] = zaz
        if i % 50 == 0:
            print(f"  detail {i + 1}/{len(zmenene)}")
        time.sleep(0.3)
    zamery = sorted((odvod(z) for z in nove.values()), key=lambda z: (z["zmena"], z["id"]), reverse=True)
    polohy(zamery, stare)
    if not zamery:
        raise RuntimeError("EIA: žiadne zámery v Bratislave")
    posledna = max(z["zmena"] for z in zamery if z["zmena"])
    zapis_ak_zmena(ULOZISKO, {"aktualizovane": datetime.now().isoformat(timespec="seconds"), "posledna_zmena": posledna,
                              "zamery": zamery}, kompaktne=True)

    # verejný výstup pre web (bez pomocných polí)
    verejne = [verejny(z) for z in zamery]
    zapis_ak_zmena(VEREJNE / "eia.json", {
        "aktualizovane": datetime.now().isoformat(timespec="seconds"),
        "zdroj": {"nazov": "Enviroportál MŽP SR / SAŽP – Informačný systém EIA/SEA", "url": "https://www.enviroportal.sk/eia", "licencia": "verejné informácie podľa zákona 24/2006 Z. z."},
        "web": WEB,
        "zamery": verejne,
    }, kompaktne=True)
    print(f"EIA Bratislava: {len(zamery)} zámerov, z toho aktívnych {sum(not z['ukoncene'] for z in zamery)}; "
          f"poloha ulica {sum(z.get('presnost') == 'ulica' for z in zamery)}, MČ {sum(z.get('presnost') == 'mc' for z in zamery)}")
    return 0


if __name__ == "__main__":
    spusti(main, "Zber EIA")
