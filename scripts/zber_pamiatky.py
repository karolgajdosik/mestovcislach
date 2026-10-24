"""Register nehnuteľných národných kultúrnych pamiatok (Ministerstvo kultúry SR) – Bratislava.

Zdroj: data.slovensko.sk – „Register nehnuteľných národných kultúrnych pamiatok – Bratislavský
samosprávny kraj“ (CSV, MK SR). Súradnice register nemá, preto ich dopĺňame z registra adries
MV SR podľa súpisného čísla, prípadne ulice a orientačného čísla.

Nezverejňujeme vlastnícku formu (pri súkromných osobách by šlo o osobný údaj) ani autora.

Výstupy:
  public/data/pamiatky-register.json – body pre mapu
  data/pamiatky-register.json        – súhrn (počty podľa mestských častí, slohov, storočí)
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from spolocne import DATA, VEREJNE, adresy_mv, norm_mc, norm_ulica, s, spusti, zapis_ak_zmena

URL = "https://data.slovensko.sk/download?id=13a86d1f-c8f2-4f14-af51-a454b6e5ae8d"
ZDROJ = {"nazov": "Ministerstvo kultúry SR – Register nehnuteľných národných kultúrnych pamiatok (Bratislavský kraj)",
         "url": "https://data.slovensko.sk/datasety", "licencia": "otvorené dáta (data.slovensko.sk)"}
CELKY = {"MPR": "pamiatková rezervácia", "PZ": "pamiatková zóna"}


def cislo(x: str) -> str:
    x = (x or "").strip()
    return "" if x in ("0", "") else x


def storocie(vznik: str) -> str | None:
    v = (vznik or "").lower()
    m = re.search(r"(\d{1,2})\.\s*st", v)
    if m:
        return f"{int(m.group(1))}. storočie"
    m = re.search(r"\b(1\d{3}|20\d{2})\b", v)
    if m:
        return f"{int(m.group(1)) // 100 + 1}. storočie"
    return None


def main() -> int:
    r = s.get(URL, timeout=300)
    r.raise_for_status()
    riadky = [x for x in csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))) if x["Okres"].startswith("Bratislava")]
    if len(riadky) < 1000:
        raise RuntimeError(f"Podozrivo málo riadkov pre Bratislavu: {len(riadky)}")

    adresy = adresy_mv()
    podla_sup: dict[tuple, tuple] = {}
    podla_ulice: dict[tuple, tuple] = {}
    for a in adresy:
        podla_sup.setdefault((a["mc"], a["sup"]), (a["lat"], a["lon"]))
        if a["ori"]:
            podla_ulice.setdefault((a["mc"], norm_ulica(a["ulica"]), a["ori"].lower()), (a["lat"], a["lon"]))

    # pamiatka (NNKP) = viac pamiatkových objektov (PO)
    pamiatky: dict[tuple, dict] = {}
    for x in riadky:
        mc = norm_mc(x["Obec"])
        if not mc:
            continue
        kluc = (mc, x["Č. ÚZPF NNKP"].strip())
        p = pamiatky.setdefault(kluc, {
            "nazov": x["Zaužívaný názov NNKP"].strip() or x["Unifikovaný názov NNKP"].strip().capitalize(),
            "typ": x["Unifikovaný názov NNKP"].strip().capitalize(), "mc": mc, "uzpf": kluc[1],
            "celok": CELKY.get(x["Chránený celok"].strip(), x["Chránený celok"].strip() or None),
            "objekty": [], "poloha": None, "adresa": None, "vznik": None, "sloh": None,
        })
        ulica = re.sub(r"\s*ul\.?$", "", x["Adresa"].strip())
        sup, ori = cislo(x["Súpisné číslo"]), cislo(x["Orientačné číslo"])
        obj = x["Unifikovaný názov PO"].strip().capitalize()
        if x["Bližšie určenie PO"].strip():
            obj += f" ({x['Bližšie určenie PO'].strip()})"
        p["objekty"].append(obj)
        p["vznik"] = p["vznik"] or x["Vznik"].strip() or None
        p["sloh"] = p["sloh"] or x["Prevládajúci sloh"].strip() or None
        if not p["adresa"] and (ulica or sup):
            p["adresa"] = " ".join(t for t in [ulica, "/".join(c for c in [sup, ori] if c)] if t)
        if not p["poloha"]:
            p["poloha"] = (podla_sup.get((mc, sup)) if sup else None) or (podla_ulice.get((mc, norm_ulica(ulica), ori.lower())) if ulica and ori else None)

    body, bez_polohy = [], []
    for p in sorted(pamiatky.values(), key=lambda p: (p["mc"], int(re.sub(r"\D", "", p["uzpf"]) or 0))):
        det = {k: v for k, v in {"typ": p["typ"], "a": p["adresa"], "vznik": p["vznik"], "sloh": p["sloh"], "celok": p["celok"],
                                  "obj": p["objekty"][:6] + ([f"a ďalšie ({len(p['objekty']) - 6})"] if len(p["objekty"]) > 6 else []), "uzpf": p["uzpf"], "mc": p["mc"]}.items() if v}
        if p["poloha"]:
            body.append([round(p["poloha"][0], 5), round(p["poloha"][1], 5), p["nazov"], det])
        else:
            bez_polohy.append([p["nazov"], det])

    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    verejne = {"zdroj": ZDROJ, "body": body, "bez_polohy": bez_polohy, "aktualizovane": teraz}
    po_mc = Counter(p["mc"] for p in pamiatky.values())
    suhrn = {
        "zdroj": ZDROJ, "pamiatok": len(pamiatky), "objektov": len(riadky), "s_polohou": len(body),
        "mestske_casti": dict(sorted(po_mc.items(), key=lambda x: -x[1])),
        "slohy": dict(Counter(p["sloh"] for p in pamiatky.values() if p["sloh"]).most_common(12)),
        "storocia": dict(sorted(Counter(st for p in pamiatky.values() if (st := storocie(p["vznik"]))).items(), key=lambda x: int(x[0].split(".")[0]))),
        "typy": dict(Counter(p["typ"] for p in pamiatky.values()).most_common(15)),
        "aktualizovane": teraz,
    }
    print(f"Pamiatok {len(pamiatky)} ({len(riadky)} objektov), s polohou {len(body)}; bez polohy napr.: {[b[0] for b in bez_polohy[:8]]}")
    zapis_ak_zmena(VEREJNE / "pamiatky-register.json", verejne, kompaktne=True)
    zapis_ak_zmena(DATA / "pamiatky-register.json", suhrn)
    return 0


if __name__ == "__main__":
    spusti(main, "Zber pamiatok")
