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
    return b.decode("utf-8-sig", errors="cp1250")


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
    roky: dict[str, list] = {}
    for rok, url in URL_CSD.items():
        r = s.get(url, timeout=120)
        r.raise_for_status()
        useky = []
        for riadok in dekoduj(r.content).splitlines():
            c = [x.strip() for x in riadok.split(";")]
            if len(c) >= 7 and re.match(r"^\d{5}$", c[0]) and c[2].startswith("Bratislava"):
                try:
                    useky.append({"usek": c[0], "cesta": c[1], "okres": c[2], "nakladne": int(c[3] or 0), "osobne": int(c[4] or 0), "motocykle": int(c[5] or 0), "spolu": int(c[6] or 0)})
                except ValueError:
                    pass
        roky[str(rok)] = useky
    cesty = sorted({u["cesta"] for v in roky.values() for u in v}, key=lambda c: (not c.startswith("D"), not c.startswith("R"), c))
    prehlad = []
    for cesta in cesty:
        riadok = {"cesta": cesta}
        for rok, useky in roky.items():
            u = [x for x in useky if x["cesta"] == cesta]
            if u:
                riadok[rok] = {"usekov": len(u), "priemer": round(sum(x["spolu"] for x in u) / len(u)), "max": max(x["spolu"] for x in u),
                               "nakladne_podiel": round(100 * sum(x["nakladne"] for x in u) / max(1, sum(x["spolu"] for x in u)), 1)}
        prehlad.append(riadok)
    if not roky.get("2015"):
        raise RuntimeError("CSD 2015: žiadne bratislavské úseky")
    return {"roky": list(roky), "cesty": prehlad, "useky_2015": sorted(roky["2015"], key=lambda u: -u["spolu"]),
            "zdroj": {"nazov": "Slovenská správa ciest – celoštátne sčítanie dopravy", "url": "https://www.ssc.sk"},
            "popis": "Ročný priemer denných intenzít (vozidlá za 24 hodín) na sčítacích úsekoch diaľnic a ciest I. až III. triedy v okresoch Bratislava I–V. Miestne komunikácie mesta sa nesčítavajú."}


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
