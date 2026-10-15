"""Školy v Bratislave z rezortných dát MŠVVaM SR: počty žiakov, učiteľov, rozpočet, záujem o stredné školy.

Zdroje (data.slovensko.sk):
  „Digitálna mapa škôl“ – mapaskol.iedu.sk/data-set.aspx (CSV): škola, adresa, web, žiaci,
    pedagógovia, rozpočet, GPS.
  „Naplnenosť škôl a možnosti štúdia“ – www.svs.edu.sk/data-set.aspx (CSV): plán prijatia,
    záujem uchádzačov a zapísaní na stredných školách podľa odborov.

Výstupy:
  public/data/skoly-iedu.json – body pre mapu
  data/skoly-iedu.json        – súhrn podľa mestských častí, najväčšie školy, záujem o SŠ
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, VEREJNE, mc_podla_polohy, s, spusti, zapis_ak_zmena

URL_MAPA = "https://mapaskol.iedu.sk/data-set.aspx"
URL_SVS = "https://www.svs.edu.sk/data-set.aspx"
ZDROJ_MAPA = {"nazov": "MŠVVaM SR – Digitálna mapa škôl", "url": "https://mapaskol.iedu.sk", "licencia": "otvorené dáta (data.slovensko.sk)"}
ZDROJ_SVS = {"nazov": "MŠVVaM SR – Naplnenosť škôl a možnosti štúdia", "url": "https://www.svs.edu.sk", "licencia": "otvorené dáta (data.slovensko.sk)"}

TYPY = {"ms": "Materské školy", "zs": "Základné školy", "ss": "Stredné školy", "spec": "Špeciálne školy", "zus": "Umelecké školy (ZUŠ)", "cvc": "Centrá voľného času"}
PRAVIDLA = [
    (None, r"jedáleň|jedalen|\bŠJ\b|VŠJ|výdaj|ŠKD|klub detí|intern|inernát|inter\.|Elok\.\s*prac|CPP|poraden|Jazyková|\bJŠ\b"),
    ("ms", r"\bMŠ|materská|Mater\.|SMŠ"),
    ("zus", r"ZUŠ|umeleck\w* škola\b(?!.*priem)"),
    ("cvc", r"CVČ|voľného času"),
    ("spec", r"Špec|ŠZŠ|Diag|Liečeb|Reedukač|Odbor\.\s*učil|Prakt|pre TP|mim\.\s*nad|\bOU\b"),
    ("zs", r"\bZŠ|Základná"),
    ("ss", r"[Gg]ym|SOŠ|SPŠ|\bOA\b|\bHA\b|SZŠ|[Kk]onz|lýceum|ŠUP|umeleckého priem|SŠ|SUŠ|Tanečn|Bilingv|CSOŠ|akadém|stredn"),
]


def typ(nazov: str) -> str | None:
    for t, r in PRAVIDLA:
        if re.search(r, nazov, re.I):
            return t
    return "ine"


def num(x: str) -> float | None:
    x = re.sub(r"[\s €]", "", x or "").replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None


def citaj(url: str) -> list[dict]:
    r = s.get(url, timeout=300)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))


def kratky(nazov: str) -> str:
    return re.sub(r"\s+-\s+Bratislava,\s*", ", ", nazov).strip()


def main() -> int:
    najdi_mc = mc_podla_polohy()
    riadky = citaj(URL_MAPA)
    if len(riadky) < 5000:
        raise RuntimeError(f"Digitálna mapa škôl: málo riadkov ({len(riadky)})")
    body, skoly = [], []
    for x in riadky:
        lat, lon = num(x.get("GPS1")), num(x.get("GPS2"))
        if not lat or not lon or not (47.9 < lat < 48.35 and 16.8 < lon < 17.4):
            continue
        mc = najdi_mc(lon, lat)
        if not mc:
            continue
        t = typ(x["Názov"])
        if not t or t == "ine":
            continue
        zs = {"nazov": kratky(x["Názov"]), "typ": t, "mc": mc, "ziaci": num(x["Počet žiakov"]), "ped": num(x["Počet ped.zam."]),
              "rozpocet": num(x["Rozpočet v 2024"]), "web": (x.get("Web stránka") or "").strip(), "adresa": x["Ulica"].strip(),
              "jazyk": (x.get("Vyuč.jaz.") or "").strip(), "eduid": x["EDUID"].strip()}
        skoly.append(zs)
        det = {k: v for k, v in {"a": zs["adresa"], "w": zs["web"] and ("https://" + zs["web"] if not zs["web"].startswith("http") else zs["web"]),
                                  "z": zs["ziaci"] and int(zs["ziaci"]), "ped": zs["ped"], "roz": zs["rozpocet"] and int(zs["rozpocet"]),
                                  "jaz": zs["jazyk"] if zs["jazyk"] not in ("", "Nesleduje sa", "Slovenský") else None}.items() if v}
        body.append([round(lat, 5), round(lon, 5), t, zs["nazov"], det])
    if len(body) < 400:
        raise RuntimeError(f"Málo škôl v Bratislave ({len(body)})")

    # súhrn podľa mestských častí a typov
    po_mc: dict = defaultdict(lambda: defaultdict(lambda: {"skol": 0, "ziakov": 0}))
    for sk in skoly:
        p = po_mc[sk["mc"]][sk["typ"]]
        p["skol"] += 1
        p["ziakov"] += int(sk["ziaci"] or 0)
    mesto = {t: {"skol": sum(po_mc[m][t]["skol"] for m in po_mc), "ziakov": sum(po_mc[m][t]["ziakov"] for m in po_mc)} for t in TYPY}
    for t in ("zs", "ss"):  # pri MŠ, ZUŠ a CVČ sa pedagógovia počítajú inak – pomer nedáva zmysel
        ss = [sk for sk in skoly if sk["typ"] == t and sk["ziaci"] and sk["ped"]]
        mesto[t]["ziakov_na_ucitela"] = round(sum(sk["ziaci"] for sk in ss) / sum(sk["ped"] for sk in ss), 1) if ss else None
    najvacsie = {t: [{"nazov": sk["nazov"], "mc": sk["mc"], "ziaci": int(sk["ziaci"])} for sk in sorted((sk for sk in skoly if sk["typ"] == t and sk["ziaci"]), key=lambda sk: -sk["ziaci"])[:10]]
                 for t in ("zs", "ss", "ms")}

    # záujem o stredné školy (prijímacie konanie)
    zaujem = []
    try:
        svs = [x for x in citaj(URL_SVS) if x.get("Kraj", "").startswith("Bratislav") and "Bratislava" in x.get("Obec", "")]
        agg: dict = defaultdict(lambda: {"plan": 0, "zaujem1": 0, "zaujem12": 0, "zapisani": 0})
        for x in svs:
            k = (x["Názov školy"].strip(), x["Ulica"].strip(), x["Obec"].strip())
            a = agg[k]
            a["plan"] += int(num(x.get("Celkový plán")) or 0)
            a["zaujem1"] += int(num(x.get("1. záujem")) or 0)
            a["zaujem12"] += int(num(x.get("1.+2. záujem")) or 0)
            a["zapisani"] += int(num(x.get("Zapísaní")) or 0)
        for (nazov, ulica, obec), a in agg.items():
            if a["zaujem12"] > 0:
                zaujem.append({"nazov": nazov, "adresa": ulica, "mc": obec.replace("Bratislava-", ""), **a,
                               "zaujem_na_miesto": round(a["zaujem1"] / a["plan"], 2) if a["plan"] >= 10 else None})
        # plán prijatia je pri mnohých školách prázdny – poradie podľa prihlášok s 1. voľbou
        zaujem.sort(key=lambda z: -z["zaujem1"])
        print(f"Naplnenosť SŠ: {len(svs)} odborov, {len(zaujem)} škôl")
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Naplnenosť škôl::{e}")

    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zapis_ak_zmena(VEREJNE / "skoly-iedu.json", {"zdroj": ZDROJ_MAPA, "typy": TYPY, "body": body, "aktualizovane": teraz}, kompaktne=True)
    suhrn = {
        "zdroj": ZDROJ_MAPA, "zdroj_zaujem": ZDROJ_SVS, "typy": TYPY, "rok_rozpoctu": 2024, "mesto": mesto,
        "mestske_casti": {m: {t: v for t, v in d.items()} for m, d in sorted(po_mc.items())},
        "najvacsie": najvacsie,
        "zaujem_ss": {"skol": len(zaujem), "plan": sum(z["plan"] for z in zaujem), "zaujem1": sum(z["zaujem1"] for z in zaujem),
                      "zaujem12": sum(z["zaujem12"] for z in zaujem), "zapisani": sum(z["zapisani"] for z in zaujem), "najzaujimavejsie": zaujem[:15]},
        "aktualizovane": teraz,
    }
    zapis_ak_zmena(DATA / "skoly-iedu.json", suhrn)
    print(f"Škôl na mape {len(body)}; {', '.join(f'{TYPY[t]} {v['skol']} ({v['ziakov']} žiakov)' for t, v in mesto.items())}")
    return 0


if __name__ == "__main__":
    spusti(main, "Zber škôl (iedu)")
