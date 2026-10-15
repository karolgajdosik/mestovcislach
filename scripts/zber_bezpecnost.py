"""Bezpečnosť a podnety: udalosti mestskej polície (2017–2022) a podnety občanov magistrátu (od 2017).

Zdroje (data.bratislava.sk, CC BY 4.0):
  Počet priestupkov podľa druhu udalosti v rokoch 2017–2022 (342 tisíc záznamov)
  Počet podozrení o spáchaní trestného činu 2017–2022, Počet ostatných udalostí 2017–2022
  Počet priestupkov a výška pokút
  Práca s podnetmi zadanými Magistrátu (od 2017)

Zverejňujeme súhrny (roky, mestské časti, ulice, druhy, hodiny a dni). Pri podnetoch nezverejňujeme
nadpisy ani texty (môžu obsahovať osobné údaje) – len kategóriu, stav, mestskú časť a polohu.

Výstupy:
  data/bezpecnost-bratislava.json    – súhrny pre stránku /bezpecnost a asistenta
  public/data/podnety-bratislava.json – body podnetov za posledných 12 mesiacov (mapa)
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import median

from diakritika import hodnota as s_diakritikou
from spolocne import url_vrstvy, DATA, VEREJNE, mc_podla_polohy, norm_mc, s, spusti, zapis_ak_zmena

ITEM = "https://www.arcgis.com/sharing/rest/content/items/{}"
UDALOSTI = {"priestupky": "2566d894", "trestne_ciny": "22a2a9f6", "ostatne": "45348130"}
POKUTY, PODNETY = "d3d71db2", "96b70a02"
ZNAME_STAVY = {"V riešení", "Vyriešený", "Uzavretý", "Neriešený", "Odoslaný", "Prijatý", "Zamietnutý", "Presmerovaný"}
DNI = ["pondelok", "utorok", "streda", "štvrtok", "piatok", "sobota", "nedeľa"]


def plne_id(prefix: str) -> str:
    for p in json.loads((DATA / "katalog-bratislava.json").read_text(encoding="utf-8"))["datasety"]:
        if p["id"].startswith(prefix):
            return p["id"]
    raise RuntimeError(f"{prefix} nie je v inventári")


def riadky(prefix: str) -> list[dict]:
    url = url_vrstvy(plne_id(prefix))
    vysl, offset = [], 0
    while True:
        r = s.get(url + "/query", params={"where": "1=1", "outFields": "*", "returnGeometry": "false", "resultOffset": offset,
                                          "resultRecordCount": 2000, "f": "json"}, timeout=240).json()
        if "error" in r:
            raise RuntimeError(r["error"])
        f = [x["attributes"] for x in r.get("features", [])]
        vysl += f
        if len(f) < 2000 and not r.get("exceededTransferLimit"):
            return vysl
        offset += len(f)


def cas(v) -> datetime | None:
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, timezone.utc).replace(tzinfo=None)
    t = str(v or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{1,2}):(\d{2}))?", t) or None
    if m:
        y, mo, d, h, mi = m.groups()
        return datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0))
    m = re.match(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", t)
    if m:
        d, mo, y, h, mi = m.groups()
        try:
            return datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0))
        except ValueError:
            return None
    return None


def t(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def suhrn_udalosti(data: list[dict]) -> dict:
    po_rokoch, po_mc, druhy, skupiny = Counter(), defaultdict(Counter), Counter(), Counter()
    ulice, hodiny, dni, mc_druhy = Counter(), Counter(), Counter(), defaultdict(Counter)
    ma_cas = 0
    for r in data:
        c = cas(r.get("Dátum_a_čas_od"))
        mc = norm_mc(t(r.get("Mestská_časť"))) or s_diakritikou(t(r.get("Mestská_časť"))) or "neuvedená"
        druh, skupina = t(r.get("Druh_udalosti")), t(r.get("Skupina_udalosti"))
        if c:
            po_rokoch[c.year] += 1
            po_mc[mc][c.year] += 1
            if c.hour or c.minute:
                ma_cas += 1
                hodiny[c.hour] += 1
            dni[c.weekday()] += 1
        druhy[druh] += 1
        skupiny[skupina] += 1
        mc_druhy[mc][druh] += 1
        ul = t(r.get("Ulica"))
        if ul:
            ulice[(ul, mc)] += 1
    return {
        "spolu": len(data), "roky": {str(k): v for k, v in sorted(po_rokoch.items())},
        "mestske_casti": {mc: {"spolu": sum(c.values()), "roky": {str(k): v for k, v in sorted(c.items())}, "najcastejsie": [d for d, _ in mc_druhy[mc].most_common(3)]}
                          for mc, c in sorted(po_mc.items(), key=lambda x: -sum(x[1].values()))},
        "druhy": [{"druh": d, "pocet": n} for d, n in druhy.most_common(20)],
        "skupiny": [{"skupina": d, "pocet": n} for d, n in skupiny.most_common(12)],
        "ulice": [{"ulica": u, "mc": mc, "pocet": n} for (u, mc), n in ulice.most_common(25)],
        "hodiny": [hodiny.get(h, 0) for h in range(24)] if ma_cas > len(data) * 0.5 else None,
        "dni": [dni.get(d, 0) for d in range(7)],
    }


def main() -> int:
    vystup: dict = {"zdroj": {"nazov": "Mestská polícia hlavného mesta SR Bratislavy a magistrát – data.bratislava.sk", "url": "https://data.bratislava.sk", "licencia": "CC BY 4.0"}, "dni": DNI}
    chyby = []
    for kluc, prefix in UDALOSTI.items():
        try:
            data = riadky(prefix)
            vystup[kluc] = suhrn_udalosti(data)
            print(f"{kluc}: {len(data)} záznamov; ukážka času {data[0].get('Dátum_a_čas_od')!r}; roky {vystup[kluc]['roky']}")
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{kluc}: {e}")
    try:
        po_rokoch: dict[int, dict] = defaultdict(lambda: defaultdict(lambda: {"pocet": 0, "suma": 0.0}))
        for r in riadky(POKUTY):
            c = cas(r.get("Dátum"))
            if not c:
                continue
            try:
                suma = float(str(r.get("BP_v_EUR") or 0).replace(",", "."))
            except ValueError:
                suma = 0.0
            p = po_rokoch[c.year][t(r.get("Skupina_udalosti")) or "iné"]
            p["pocet"] += 1
            p["suma"] += suma
        vystup["pokuty"] = {str(y): {sk: {"pocet": v["pocet"], "suma": round(v["suma"])} for sk, v in sorted(g.items(), key=lambda x: -x[1]["pocet"])}
                            for y, g in sorted(po_rokoch.items())}
    except Exception as e:  # noqa: BLE001
        chyby.append(f"pokuty: {e}")

    # Podnety občanov
    try:
        najdi_mc = mc_podla_polohy()
        data = riadky(PODNETY)
        print("Podnety ukážka:", {k: data[0].get(k) for k in ("DATUM_PRIDANIA", "DATUM_UKONCENIA", "STATUS", "KATEGORIA", "MESTSKA_CAST", "LATITUDE", "LONGTITUDE")})
        po_rokoch, kategorie, stavy, po_mc, dni_riesenia = Counter(), Counter(), Counter(), Counter(), defaultdict(list)
        body, posledny = [], None
        for r in data:
            c = cas(r.get("DATUM_PRIDANIA"))
            if c:
                posledny = max(posledny, c) if posledny else c
        hranica = (posledny or datetime.now()) - timedelta(days=365)
        for r in data:
            c = cas(r.get("DATUM_PRIDANIA"))
            kat = t(r.get("KATEGORIA")) or "iné"
            stav = next((x for x in (t(r.get("STATUS")), t(r.get("STAV_POZIADAVKY"))) if x in ZNAME_STAVY), "iný")
            if c:
                po_rokoch[c.year] += 1
            kategorie[kat] += 1
            stavy[stav] += 1
            mc = norm_mc(t(r.get("MESTSKA_CAST"))) or "neuvedená"
            po_mc[mc] += 1
            k = cas(r.get("DATUM_UKONCENIA"))
            if c and k and k >= c:
                dni_riesenia[c.year].append((k - c).days)
            try:
                lat, lon = float(str(r.get("LATITUDE")).replace(",", ".")), float(str(r.get("LONGTITUDE")).replace(",", "."))
            except (TypeError, ValueError):
                continue
            if c and c >= hranica and najdi_mc(lon, lat):
                body.append([round(lat, 5), round(lon, 5), kat, t(r.get("PODKATEGORIA")), stav, c.date().isoformat()])
        vystup["podnety"] = {
            "spolu": len(data), "roky": {str(k): v for k, v in sorted(po_rokoch.items())},
            "kategorie": [{"kategoria": k, "pocet": n} for k, n in kategorie.most_common(15)],
            "stavy": dict(stavy.most_common()), "mestske_casti": dict(po_mc.most_common()),
            "median_dni_vyriesenia": {str(k): median(v) for k, v in sorted(dni_riesenia.items()) if len(v) > 20},
            "posledny_podnet": posledny.date().isoformat() if posledny else None,
        }
        zapis_ak_zmena(VEREJNE / "podnety-bratislava.json", {"zdroj": vystup["zdroj"], "od": hranica.date().isoformat(), "body": body,
                                                            "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")}, kompaktne=True)
        print(f"Podnety: {len(data)}, na mape {len(body)} (od {hranica.date()})")
    except Exception as e:  # noqa: BLE001
        chyby.append(f"podnety: {e}")
    if chyby:
        print("Chyby:", chyby)
    if not vystup.get("priestupky"):
        raise RuntimeError("; ".join(chyby))
    vystup["chyby"] = chyby
    vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zapis_ak_zmena(DATA / "bezpecnost-bratislava.json", vystup)
    return 0


if __name__ == "__main__":
    spusti(main, "Zber bezpečnosti a podnetov")
