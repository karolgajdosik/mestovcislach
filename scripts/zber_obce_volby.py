"""Výsledky celoštátnych volieb za všetky obce (ŠÚ SR, volby.statistics.sk/opendata).

  NRSR 2023, EP 2024 – tab02d (účasť po obciach), tab03e (hlasy strán po obciach), tab01 (SR).
  Prezident 2024 – ak je k dispozícii (PREZ_ZDROJE), inak sa vynechá.

Výstup data/obce/volby.json:
  {"volby": {id: {"nazov", "strany": [názvy], "sr": {"ucast", "s": [[i, %], …]}, "okresy": {okres: ucast},
                  "obce": {kód: [ucast, [[i, %], … top 6]]}}}}
Mená kandidátov na prezidenta sú verejní kandidáti (meno + hlasy) – rovnaké pravidlo ako pri poslancoch.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE, cislo

URL = "https://volby.statistics.sk/opendata"
VOLBY = [("nrsr2023", "Parlamentné voľby 2023", "nrsr/2023/NRSR2023_SK"), ("ep2024", "Eurovoľby 2024", "eup/2024/EP2024_SK"),
         ("prez2024_1", "Prezidentské voľby 2024 – 1. kolo", "zip:https://volby.statistics.sk/prez/prez2024/files/kolo1/PREZ2024_kolo1_SK_csv.zip"),
         ("prez2024_2", "Prezidentské voľby 2024 – 2. kolo", "zip:https://volby.statistics.sk/prez/prez2024/files/kolo2/PREZ2024_kolo2_SK_csv.zip")]
KODY = {o["kod"] for o in OBCE}
OKRES = {o["kod"]: o["okres"] for o in OBCE}


def csv_url(url: str) -> list[dict]:
    r = s.get(url, timeout=300)
    r.raise_for_status()
    t = r.content.decode("utf-8-sig")
    hl = t.split("\n", 1)[0]
    return list(csv.DictReader(io.StringIO(t), delimiter=";" if hl.count(";") > hl.count(",") else ","))


def stlpec(riadok: dict, *vzory: str) -> str:
    for k in riadok:
        if all(v.lower() in k.lower() for v in vzory):
            return k
    raise KeyError(f"stĺpec {vzory} nie je v {list(riadok)[:12]}")


def citaj_csv(t: str) -> list[dict]:
    hl = t.split("\n", 1)[0]
    return list(csv.DictReader(io.StringIO(t), delimiter=";" if hl.count(";") > hl.count(",") else ","))


def tabulky(cesta: str) -> tuple[list[dict], list[dict], dict]:
    if cesta.startswith("zip:"):
        import zipfile
        r = s.get(cesta[4:], timeout=300)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        nac = lambda kon: citaj_csv(z.read(next(n for n in z.namelist() if n.endswith(kon))).decode("utf-8-sig"))  # noqa: E731
        return nac("_tab02d.csv"), nac("_tab03e.csv"), nac("_tab01.csv")[0]
    return csv_url(f"{URL}/{cesta}_tab02d.csv"), csv_url(f"{URL}/{cesta}_tab03e.csv"), csv_url(f"{URL}/{cesta}_tab01.csv")[0]


def jedny(vid: str, nazov: str, cesta: str) -> dict:
    ucast, hlasy, sr = tabulky(cesta)
    k_kod, k_zap, k_zuc = stlpec(ucast[0], "kód obce"), stlpec(ucast[0], "zapísaných"), stlpec(ucast[0], "zúčastnených")
    h_kod, h_hl = stlpec(hlasy[0], "kód obce"), stlpec(hlasy[0], "počet platných hlasov")
    if any("politického subjektu" in k for k in hlasy[0]):
        h_str = stlpec(hlasy[0], "politického subjektu")
        meno = lambda h: h[h_str].strip()  # noqa: E731
    else:  # prezidentské voľby – kandidát (verejná funkcia: meno a hlasy)
        meno = lambda h: f"{h['Meno'].strip()} {h['Priezvisko'].strip()}"  # noqa: E731
    zap: dict[str, float] = defaultdict(float)
    zuc: dict[str, float] = defaultdict(float)
    for u in ucast:
        k = u[k_kod].strip()
        zap[k] += cislo(u[k_zap]) or 0
        zuc[k] += cislo(u[k_zuc]) or 0
    po: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    sr_strany: dict[str, float] = defaultdict(float)
    for h in hlasy:
        n = meno(h)
        v = cislo(h[h_hl]) or 0
        po[h[h_kod].strip()][n] += v
        sr_strany[n] += v
    strany = [n for n, _ in sorted(sr_strany.items(), key=lambda x: -x[1])]
    idx = {n: i for i, n in enumerate(strany)}
    spolu_sr = sum(sr_strany.values()) or 1
    obce = {}
    for kod, st in po.items():
        if kod not in KODY or not zap.get(kod):
            continue
        sp = sum(st.values()) or 1
        obce[kod] = [round(100 * zuc[kod] / zap[kod], 1), [[idx[n], round(100 * v / sp, 1)] for n, v in sorted(st.items(), key=lambda x: -x[1])[:6] if v > 0]]
    okr: dict[str, list] = defaultdict(lambda: [0.0, 0.0])
    for kod in obce:
        okr[OKRES[kod]][0] += zuc[kod]
        okr[OKRES[kod]][1] += zap[kod]
    print(f"{nazov}: {len(obce)} obcí, {len(strany)} strán")
    if len(obce) < 2500:
        raise RuntimeError(f"{vid}: len {len(obce)} obcí")
    return {"nazov": nazov, "strany": strany,
            "sr": {"ucast": cislo(sr.get(stlpec(sr, "účasť"))), "s": [[idx[n], round(100 * v / spolu_sr, 1)] for n, v in sorted(sr_strany.items(), key=lambda x: -x[1])[:8]]},
            "okresy": {o: round(100 * a / b, 1) for o, (a, b) in sorted(okr.items()) if b},
            "obce": dict(sorted(obce.items()))}


def main() -> int:
    stare_f = DATA / "obce" / "volby.json"
    import json
    stare = json.loads(stare_f.read_text(encoding="utf-8")).get("volby", {}) if stare_f.exists() else {}
    out = {}
    for vid, nazov, cesta in VOLBY:
        try:
            out[vid] = jedny(vid, nazov, cesta)
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Voľby obcí {vid}::{e}")
            if vid in stare:
                out[vid] = stare[vid]
    if not out:
        raise RuntimeError("žiadne voľby")
    zapis_ak_zmena(stare_f, {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "zdroj": {"nazov": "ŠÚ SR – výsledky volieb, otvorené dáta", "url": "https://volby.statistics.sk"},
                             "volby": out}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Voľby v obciach")
