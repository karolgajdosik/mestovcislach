"""Školy v 8 krajských mestách z rezortných dát MŠVVaM SR (údaje o školách ako inštitúciách, žiadne osobné údaje).

Zdroje (data.slovensko.sk):
  „Digitálna mapa škôl“ – mapaskol.iedu.sk/data-set.aspx (CSV): škola, adresa, web, počet žiakov,
    pedagógov, rozpočet, GPS.
  „Naplnenosť škôl a možnosti štúdia“ – www.svs.edu.sk/data-set.aspx (CSV): plán prijatia
    a záujem uchádzačov o stredné školy podľa odborov (spojenie cez EDUID).

Výsledky Testovania 9 a maturít po školách nie sú zverejnené ako otvorené dáta, preto tu nie sú.

Výstup: data/mesta/skoly.json
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, KOREN, s, spusti, zapis_ak_zmena
from zber_skoly_iedu import ZDROJ_MAPA, ZDROJ_SVS, URL_MAPA, URL_SVS, num, typ

MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))
TYPY = {"ms": "Materské školy", "zs": "Základné školy", "ss": "Stredné školy", "spec": "Špeciálne školy", "zus": "Základné umelecké školy"}


def citaj(url: str) -> list[dict]:
    r = s.get(url, timeout=300)
    r.raise_for_status()
    for kod in ("utf-8-sig", "cp1250"):
        try:
            t = r.content.decode(kod)
            break
        except UnicodeDecodeError:
            continue
    return list(csv.DictReader(io.StringIO(t), delimiter=";"))


def obec(x: str) -> str:
    """„811 01 Bratislava-Staré Mesto“ → „Bratislava-Staré Mesto“."""
    return re.sub(r"^\s*\d{3}\s?\d{2}\s+", "", x or "").strip()


def patri(o: str, mesto: str) -> bool:
    return o == mesto or o.startswith(mesto + "-") or o.startswith(mesto + " -")


def kratky(nazov: str, mesto: str) -> str:
    n = re.sub(r"\s+", " ", nazov).strip()
    n = re.sub(rf",?\s*-?\s*{re.escape(mesto)}(-[\w .]+)?\s*$", "", n)  # koncové „, Trenčín“
    n = re.sub(rf"\s+-\s+{re.escape(mesto)}\b.*?,\s*", ", ", n)
    return n.strip(" ,-")


def main() -> int:
    riadky = citaj(URL_MAPA)
    if len(riadky) < 5000:
        raise RuntimeError(f"Digitálna mapa škôl: málo riadkov ({len(riadky)})")
    rok_rozpoctu = next((int(m.group(1)) for k in riadky[0] for m in [re.search(r"Rozpočet v (\d{4})", k)] if m), None)
    kluc_rozpoctu = f"Rozpočet v {rok_rozpoctu}" if rok_rozpoctu else None

    # záujem o stredné školy podľa EDUID
    zaujem: dict = defaultdict(lambda: {"plan": 0, "z1": 0, "z12": 0, "zap": 0, "odbory": 0})
    try:
        for x in citaj(URL_SVS):
            # spojenie s digitálnou mapou škôl: kód školy (KODSKO), inak EDUID
            kody = [k for k in ((x.get("KODSKO") or "").strip(), (x.get("EDUID") or "").strip()) if k]
            if not kody:
                continue
            a = zaujem[kody[0]]
            for k in kody[1:]:
                zaujem[k] = a
            a["plan"] += int(num(x.get("Celkový plán")) or 0)
            a["z1"] += int(num(x.get("1. záujem")) or 0)
            a["z12"] += int(num(x.get("1.+2. záujem")) or 0)
            a["zap"] += int(num(x.get("Zapísaní")) or 0)
            a["odbory"] += 1
        print(f"Naplnenosť SŠ: {len(set(map(id, zaujem.values())))} škôl")
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Naplnenosť škôl::{e}")

    vystup = {}
    for m in (m for m in MESTA if m.get("aktivne")):
        nazov, skoly = m["nazov"], []
        for x in riadky:
            o = obec(x.get("Obec", ""))
            if not patri(o, nazov):
                continue
            t = typ(x["Názov"])
            if t == "ms" and re.search(r"\bZŠ|Základná", x["Názov"]):
                t = "zs"  # „ZŠ s MŠ“ je základná škola (s materskou školou)
            if t not in TYPY or re.match(r"EP\b|Elok", x["Názov"].strip()):  # elokované pracoviská sú súčasťou inej školy
                continue
            z, ped = num(x.get("Počet žiakov")), num(x.get("Počet ped.zam."))
            roz = num(x.get(kluc_rozpoctu)) if kluc_rozpoctu else None
            lat, lon = num(x.get("GPS1")), num(x.get("GPS2"))
            web = (x.get("Web stránka") or "").strip()
            sk = {
                "n": kratky(x["Názov"], nazov), "t": t, "a": (x.get("Ulica") or "").strip(),
                "mc": o.split("-", 1)[1].strip() if "-" in o else None,
                "z": int(z) if z else 0, "ped": ped,
                "uc": round(z / ped, 1) if z and ped and t in ("zs", "ss") else None,
                "rz": round(roz / z) if roz and z and z >= 20 else None,
                "w": web and (web if web.startswith("http") else "https://" + web),
                "jaz": (x.get("Vyuč.jaz.") or "").strip() if (x.get("Vyuč.jaz.") or "").strip() not in ("", "Nesleduje sa", "Slovenský", "slovenský") else None,
                "g": [round(lat, 5), round(lon, 5)] if lat and lon else None,
                "id": (x.get("EDUID") or "").strip(),
            }
            zj = zaujem.get((x.get("Kód školy") or "").strip()) or zaujem.get(sk["id"])
            if t == "ss" and zj and zj["z12"] > 0:
                sk.update({"plan": zj["plan"], "z1": zj["z1"], "z12": zj["z12"], "zap": zj["zap"], "odb": zj["odbory"],
                           "nm": round(zj["z1"] / zj["plan"], 2) if zj["plan"] >= 10 else None})
            skoly.append({k: v for k, v in sk.items() if v not in (None, "", [])})
        if len(skoly) < 20:
            print(f"::warning title=Školy {nazov}::len {len(skoly)} škôl")
        skoly.sort(key=lambda x: (list(TYPY).index(x["t"]), x["n"]))
        suhrn = {}
        for t in TYPY:
            ss = [x for x in skoly if x["t"] == t]
            pom = [x for x in ss if x.get("z") and x.get("ped")]
            suhrn[t] = {"skol": len(ss), "ziakov": sum(x.get("z", 0) for x in ss),
                        "ziakov_na_ucitela": round(sum(x["z"] for x in pom) / sum(x["ped"] for x in pom), 1) if pom and t in ("zs", "ss") else None}
        vystup[m["slug"]] = {"suhrn": suhrn, "skoly": skoly}
        print(f"{nazov}: SŠ so záujmom {sum(1 for x in skoly if 'z1' in x)}/{suhrn['ss']['skol']}")
        print(f"{nazov}: {len(skoly)} škôl – " + ", ".join(f"{t} {v['skol']}" for t, v in suhrn.items()))

    zapis_ak_zmena(DATA / "mesta" / "skoly.json", {
        "zdroj": ZDROJ_MAPA, "zdroj_zaujem": ZDROJ_SVS, "typy": TYPY, "rok_rozpoctu": rok_rozpoctu,
        "mesta": vystup, "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return 0


if __name__ == "__main__":
    spusti(main, "Zber škôl v mestách (iedu)")
