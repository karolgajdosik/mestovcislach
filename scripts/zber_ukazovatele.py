"""Ukazovatele mestských častí z celoštátnych zdrojov a celoštátne sčítanie dopravy.

Zdroje (data.slovensko.sk):
  Index regionálneho rozvoja BA kraj podľa obcí (MIRRI SR) – CSV
  Dlh a dlhová služba miest a obcí SR k ultimu roka (MF SR, opendata.mfsr.sk) – XLSX za roky
  Celoštátne sčítanie dopravy 2005, 2010, 2015 (Slovenská správa ciest) – CSV

Výstupy:
  data/mc-ukazovatele.json – index rozvoja a dlh mestských častí a mesta
  data/csd-bratislava.json – intenzita dopravy na diaľniciach a cestách I. triedy v Bratislave
"""

from __future__ import annotations

import codecs
import csv
import io
import re
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, norm_mc, s, spusti, zapis_ak_zmena

URL_INDEX = "https://data.slovensko.sk/download?id=42ea0b0c-ae52-4641-af70-47bdfe528fff"
URL_DLH = "https://opendata.mfsr.sk/opendata/download/dlh-a-dlhova-sluzba-miest-a-obci-sr-k-ultimu-roka/{}"
URL_CSD = {2005: "https://www.ssc.sk/files/documents/dopravne-inzinierstvo/csd_2005_sr.csv",
           2010: "https://www.ssc.sk/files/documents/dopravne-inzinierstvo/csd_2010/csd_2010_sr.csv",
           2015: "https://www.ssc.sk/files/documents/dopravne-inzinierstvo/csd_2015/csd_2015_sr.csv"}

# Niektoré súbory miešajú UTF-8 a jednobajtové znaky cp1250 (napr. „ž“ ako 0x9E)
codecs.register_error("cp1250", lambda e: (e.object[e.start:e.end].decode("cp1250", "replace"), e.end))


def dekoduj(b: bytes) -> str:
    t = b.decode("utf-8-sig", errors="cp1250")
    # dvojito kódované znaky (cp1250 bajt → U+0080–U+009F), napr. „ž“ ako U+009E
    return re.sub(r"[\u0080-\u009f]", lambda m: m.group(0).encode("latin-1").decode("cp1250", "replace"), t)


def mc_alebo_mesto(t: str) -> str | None:
    if not (t or "").strip().startswith("Bratislava"):  # súbory obsahujú aj Košice (napr. „Košice Staré mesto“)
        return None
    if re.search(r"hlavné mesto", t or "", re.I):
        return "Hlavné mesto"
    return norm_mc(t)


def index_rozvoja() -> dict:
    t = dekoduj(s.get(URL_INDEX, timeout=120).content)
    vysl = {}
    for x in csv.DictReader(io.StringIO(t)):
        if not x.get("Okres", "").startswith("okres Bratislava"):
            continue
        mc = norm_mc(x["Obec"])
        if mc:
            vysl[mc] = round(float(x["Skóre obce"].replace(",", ".")), 2)
    if len(vysl) != 17:
        raise RuntimeError(f"Index rozvoja: {len(vysl)} mestských častí")
    kraj = [float(x["Skóre obce"].replace(",", ".")) for x in csv.DictReader(io.StringIO(t)) if x.get("Skóre obce")]
    return {"mestske_casti": dict(sorted(vysl.items(), key=lambda x: -x[1])), "priemer_kraja": round(sum(kraj) / len(kraj), 2), "obci_v_kraji": len(kraj),
            "zdroj": {"nazov": "MIRRI SR – Index regionálneho rozvoja, Bratislavský kraj podľa obcí", "url": "https://data.slovensko.sk/datasety"},
            "popis": "Súhrnné skóre 0–100 z ukazovateľov ekonomiky, vzdelania, zdravia, bývania, infraštruktúry a životného prostredia; vyššie = rozvinutejšie."}


def stlpce(rows: list, od: int, do: int) -> dict[int, str]:
    hl: dict[int, str] = defaultdict(str)
    for r in rows[od:do]:
        for i, v in enumerate(r):
            if v is not None:
                hl[i] += " " + str(v)
    return {i: re.sub(r"\s+", " ", t).strip().lower() for i, t in hl.items()}


def najdi(hl: dict[int, str], vzor: str) -> int | None:
    for i, t in sorted(hl.items()):
        if re.search(vzor, t):
            return i
    return None


def dlh() -> dict:
    import openpyxl
    roky: dict[int, dict] = {}
    for n in range(1, 16):
        r = s.get(URL_DLH.format(n), timeout=120)
        if r.status_code != 200 or r.content[:2] != b"PK":
            continue
        wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
        list60 = next((x for x in wb.sheetnames if "60" in x and "BA" in x), None)
        list25 = next((x for x in wb.sheetnames if "25" in x and "BA" in x), None)
        if not list60:
            continue
        rows = [list(x) for x in wb[list60].iter_rows(values_only=True)]
        rok = next((int(m.group(1)) for r_ in rows[:8] for v in r_ if isinstance(v, str) and (m := re.search(r"31\.12\.(\d{4})", v))), None)
        if not rok:
            continue
        hl = stlpce(rows, 6, 11)
        i_dlh, i_prijmy, i_pomer = najdi(hl, r"celková suma"), najdi(hl, r"príjmy"), najdi(hl, r"pomer")
        data: dict[str, dict] = {}
        for r_ in rows[10:]:
            mc = mc_alebo_mesto(str(r_[0] or ""))
            if mc and i_dlh is not None:
                data[mc] = {"dlh": round(float(r_[i_dlh] or 0)), "prijmy": round(float(r_[i_prijmy] or 0)) if i_prijmy is not None else None,
                            "pomer": round(float(r_[i_pomer] or 0), 2) if i_pomer is not None else None}
        if list25:
            rows = [list(x) for x in wb[list25].iter_rows(values_only=True)]
            hl = stlpce(rows, 6, 11)
            i_pom = najdi(hl, r"pomer dlhovej")
            for r_ in rows[10:]:
                mc = mc_alebo_mesto(str(r_[0] or ""))
                if mc in data and i_pom is not None:
                    data[mc]["dlhova_sluzba"] = round(float(r_[i_pom] or 0), 2)
        if len(data) >= 17:
            roky[rok] = data
            print(f"Dlh {rok}: hlavné mesto {data.get('Hlavné mesto', {}).get('dlh')} €, Petržalka {data.get('Petržalka', {}).get('dlh')} €")
    if len(roky) < 3:
        raise RuntimeError(f"Dlh: len {len(roky)} rokov")
    return {"roky": {str(k): v for k, v in sorted(roky.items())},
            "zdroj": {"nazov": "MF SR – Dlh a dlhová služba miest a obcí SR k ultimu roka", "url": "https://opendata.mfsr.sk"},
            "popis": "Dlh podľa zákona o rozpočtových pravidlách územnej samosprávy (bez úverov ŠFRB na nájomné byty). Pomer = dlh / bežné príjmy predchádzajúceho roka v %; zákonný limit 60 %. Dlhová služba = splátky istín a úrokov / bežné príjmy; limit 25 %."}


def csd() -> dict:
    """Úseky v okresoch Bratislava I–V podľa CSD 2015; staršie roky sa priradia podľa čísla úseku
    (súbory 2005 a 2010 majú iné stĺpce a rok 2005 nemá okres)."""
    surove: dict[int, dict[str, list]] = {}
    for rok, url in URL_CSD.items():
        r = s.get(url, timeout=120)
        r.raise_for_status()
        t = r.content.decode("cp1250", "replace") if rok < 2015 else dekoduj(r.content)
        surove[rok] = {}
        for riadok in t.splitlines():
            c = [x.strip() for x in riadok.split(";")]
            if len(c) >= 7 and re.match(r"^\d{5}$", c[0]) and re.match(r"^\d+$", c[-1] or "x"):
                surove[rok][c[0]] = c
    useky_2015 = []
    for usek, c in surove[2015].items():
        if len(c) >= 8 and c[2].startswith("Bratislava"):
            useky_2015.append({"usek": usek, "cesta": c[1], "okres": c[2], "nakladne": int(c[3] or 0), "osobne": int(c[4] or 0), "motocykle": int(c[5] or 0), "spolu": int(c[6] or 0)})
    if not useky_2015:
        raise RuntimeError("CSD 2015: žiadne bratislavské úseky")
    cesta_useku = {u["usek"]: u["cesta"] for u in useky_2015}
    roky: dict[str, list] = {"2015": useky_2015}
    for rok in (2005, 2010):
        roky[str(rok)] = [{"usek": u, "cesta": cesta_useku[u], "spolu": int(c[-1]), "nakladne": int(c[-4] or 0)}
                          for u, c in surove[rok].items() if u in cesta_useku and int(c[-1] or 0) > 0]

    def nazov(cesta: str) -> str:
        if cesta.startswith(("D", "R")):
            return cesta
        return {1: "I", 3: "II", 4: "III"}.get(len(cesta), "") + "/" + cesta if len(cesta) != 2 else "I/" + cesta

    cesty = sorted({u["cesta"] for u in useky_2015}, key=lambda c: (not c.startswith("D"), len(c), c))
    prehlad = []
    for cesta in cesty:
        riadok = {"cesta": nazov(cesta)}
        for rok in ("2005", "2010", "2015"):
            u = [x for x in roky[rok] if x["cesta"] == cesta and x["spolu"] > 0]
            if u:
                riadok[rok] = {"usekov": len(u), "priemer": round(sum(x["spolu"] for x in u) / len(u)), "max": max(x["spolu"] for x in u),
                               "nakladne_podiel": round(100 * sum(x["nakladne"] for x in u) / max(1, sum(x["spolu"] for x in u)), 1) if any(x["nakladne"] for x in u) else None}
        prehlad.append(riadok)
    # porovnanie rovnakých úsekov 2005 → 2015
    spolocne_useky = [u for u in useky_2015 if u["spolu"] and any(x["usek"] == u["usek"] for x in roky["2005"])]
    s05 = {x["usek"]: x["spolu"] for x in roky["2005"]}
    narast = round(100 * (sum(u["spolu"] for u in spolocne_useky) / max(1, sum(s05[u["usek"]] for u in spolocne_useky)) - 100), 1) if spolocne_useky else None
    return {"roky": ["2005", "2010", "2015"], "cesty": prehlad, "useky_2015": sorted(useky_2015, key=lambda u: -u["spolu"])[:40],
            "narast_2005_2015": {"usekov": len(spolocne_useky), "percent": narast},
            "zdroj": {"nazov": "Slovenská správa ciest – celoštátne sčítanie dopravy", "url": "https://www.ssc.sk"},
            "popis": "Ročný priemer denných intenzít (vozidlá za 24 hodín) na sčítacích úsekoch diaľnic a ciest I. až III. triedy v okresoch Bratislava I–V. Novšie celoštátne sčítanie (2020, 2025) SSC na webe zatiaľ v rovnakom formáte nezverejnila."}


def main() -> int:
    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    chyby = []
    vystup: dict = {}
    for kluc, f in (("index_rozvoja", index_rozvoja), ("dlh", dlh)):
        try:
            vystup[kluc] = f()
        except Exception as e:  # noqa: BLE001
            chyby.append(f"{kluc}: {e}")
            print(f"CHYBA {kluc}: {e}")
    if vystup:
        stare_cesta = DATA / "mc-ukazovatele.json"
        if stare_cesta.exists():
            import json
            stare = json.loads(stare_cesta.read_text(encoding="utf-8"))
            for k in ("index_rozvoja", "dlh"):
                vystup.setdefault(k, stare.get(k))
        zapis_ak_zmena(DATA / "mc-ukazovatele.json", {**vystup, "aktualizovane": teraz})
    try:
        d = csd()
        zapis_ak_zmena(DATA / "csd-bratislava.json", {**d, "aktualizovane": teraz})
        print(f"CSD: roky {d['roky']}, ciest {len(d['cesty'])}, úsekov 2015 {len(d['useky_2015'])}")
    except Exception as e:  # noqa: BLE001
        chyby.append(f"csd: {e}")
    if chyby:
        raise RuntimeError("; ".join(chyby))
    return 0


if __name__ == "__main__":
    spusti(main, "Zber ukazovateľov MČ")
