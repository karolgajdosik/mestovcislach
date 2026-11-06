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
import re
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE, cislo

URL = "https://volby.statistics.sk/opendata"
VOLBY = [("nrsr2020", "Parlamentné voľby 2020", "nrsr2020:https://volby.statistics.sk/nrsr/nrsr2020/files/NRSR_2020_SK_csv.zip"),
         ("prez2019_1", "Prezidentské voľby 2019 – 1. kolo", "xlsx:https://volby.statistics.sk/prez/prez2019/files/PRE_2019_KOLO1_xlsx.zip"),
         ("prez2019_2", "Prezidentské voľby 2019 – 2. kolo", "xlsx:https://volby.statistics.sk/prez/prez2019/files/PRE_2019_KOLO2_xlsx.zip"),
         ("nrsr2023", "Parlamentné voľby 2023", "nrsr/2023/NRSR2023_SK"), ("ep2024", "Eurovoľby 2024", "eup/2024/EP2024_SK"),
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


def _zip(url: str):
    import zipfile
    r = s.get(url, timeout=300)
    r.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(r.content))


def _dekoduj(b: bytes) -> str:
    try:
        return b.decode("utf-8-sig")
    except UnicodeDecodeError:
        return b.decode("cp1250")


def _xlsx(z, koniec: str) -> list[dict]:
    """Tabuľka ŠÚ v xlsx: nadpis, prázdny riadok, hlavička, prázdny riadok, dáta."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith(koniec)))), read_only=True)
    riadky = list(wb.worksheets[0].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(riadky)  # hlavička = prvý riadok s aspoň 3 textovými bunkami (nadpis má jednu)
              if r and sum(isinstance(c, str) and c.strip() != "" for c in r) >= 3)
    hl = [re.sub(r"\s+", " ", str(c or "")).strip() for c in riadky[hi]]
    return [{h: ("" if c is None else str(c)) for h, c in zip(hl, r)} for r in riadky[hi + 1:] if r and any(c is not None for c in r)]


def tabulky(cesta: str) -> tuple[list[dict], list[dict], dict]:
    if cesta.startswith("nrsr2020:"):  # kódované CSV s „|“, po okrskoch; strany v tab0a
        z = _zip(cesta[9:])
        nac = lambda kon: list(csv.DictReader(io.StringIO(_dekoduj(z.read(next(n for n in z.namelist() if n.endswith(kon))))), delimiter="|"))  # noqa: E731
        strany = {r["PS"]: r["NPS"].strip() for r in nac("_tab0a.csv")}
        ucast = [{"Kód obce": r["OBEC"], "Počet zapísaných voličov": r["P_ZAP"], "Počet zúčastnených voličov": r["P_ZUC"]} for r in nac("_tab02e.csv")]
        hlasy = [{"Kód obce": r["OBEC"], "Názov politického subjektu": strany.get(r["PS"], r["PS"]), "Počet platných hlasov": r["P_HL_PS"]} for r in nac("_tab03f.csv")]
        zap = sum(cislo(u["Počet zapísaných voličov"]) or 0 for u in ucast)
        zuc = sum(cislo(u["Počet zúčastnených voličov"]) or 0 for u in ucast)
        return ucast, hlasy, {"Účasť voličov v %": str(round(100 * zuc / zap, 2))}
    if cesta.startswith("xlsx:"):  # prezidentské voľby 2019 – len xlsx
        z = _zip(cesta[5:])
        ucast = [{**r, "Počet zúčastnených voličov": r.get("Počet vydaných obálok", "")} for r in _xlsx(z, "_tab02d.xlsx")]
        return ucast, _xlsx(z, "_tab03e.xlsx"), _xlsx(z, "_tab01.xlsx")[0]
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
        h_str = stlpec(hlasy[0], "názov", "politického subjektu")
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


UCAST = [("oso2022", "Komunálne voľby 2022", "https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip"),
         ("osk2022", "Krajské voľby 2022", "https://volby.statistics.sk/osk/osk2022/files/OSK2022_SK_csv.zip"),
         ("ref2023", "Referendum 2023", "https://volby.statistics.sk/ref/ref2023/files/REF2023_SK_csv.zip")]


def len_ucast(url: str) -> dict:
    """Účasť po obciach zo súboru po okrskoch (OBEC|…|P_ZAP|P_ZUC) – voľby, kde ukazujeme len účasť."""
    z = _zip(url)
    for n in z.namelist():
        if not n.endswith(".csv"):
            continue
        txt = _dekoduj(z.read(n))
        hl = txt.split("\n", 1)[0].strip().split("|")
        if hl[:1] == ["OBEC"] and "P_ZAP" in hl and "P_ZUC" in hl:
            zap: dict[str, float] = defaultdict(float)
            zuc: dict[str, float] = defaultdict(float)
            for r in csv.DictReader(io.StringIO(txt), delimiter="|"):
                zap[r["OBEC"].strip()] += cislo(r["P_ZAP"]) or 0
                zuc[r["OBEC"].strip()] += cislo(r["P_ZUC"]) or 0
            obce = {k: round(100 * zuc[k] / v, 1) for k, v in zap.items() if v and k in KODY}
            okr: dict[str, list] = defaultdict(lambda: [0.0, 0.0])
            for k in obce:
                okr[OKRES[k]][0] += zuc[k]
                okr[OKRES[k]][1] += zap[k]
            return {"sr": round(100 * sum(zuc.values()) / sum(zap.values()), 1), "okresy": {o: round(100 * a / b, 1) for o, (a, b) in sorted(okr.items()) if b},
                    "obce": dict(sorted(obce.items()))}
    raise RuntimeError(f"{url}: nenašla sa tabuľka účasti po okrskoch")


def starosta2022() -> None:
    """Voľby starostu/primátora 2022 – kandidáti (len meno, titul, strana) a hlasy po obciach → starosta2022.json.
    Vek a zamestnanie kandidátov sa neukladajú."""
    import csv
    import io
    z = _zip("https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_csv.zip")
    def tab(kon: str) -> list[dict]:
        n = next(x for x in z.namelist() if x.endswith(kon))
        return list(csv.DictReader(io.StringIO(_dekoduj(z.read(n))), delimiter="|"))
    strany = {x["PS"].strip(): (x.get("SNPS") or x.get("NPS") or "").strip() for x in tab("_tab0c.csv")}
    kand: dict[tuple[str, str], dict] = {}
    for x in tab("_tab0ad.csv"):
        ps = [c.strip() for c in (x.get("PS") or "").split(",") if c.strip()]
        sn = [strany.get(c) for c in ps if strany.get(c)]
        tituly = [c.strip() for c in (x.get("TITUL") or "").split(",") if c.strip()]
        za = [c for c in tituly if re.match(r"^(PhD|CSc|DrSc|ArtD|MBA|MPH|LL\.?M|MSc|MA|BSBA|DBA|MPA)\.?$", c)]
        pred = [c for c in tituly if c not in za]
        meno = " ".join(v for v in (" ".join(pred), x["MENO"].strip(), x["PRIEZVISKO"].strip()) if v) + (", " + ", ".join(za) if za else "")
        sn = [n for n in sn if not re.search(r"NEKA|^NK\b", n)]
        kand[(x["OBEC"].strip(), x["PC_HL"].strip())] = {"m": meno, "s": ", ".join(sn) if sn else "nezávislý kandidát", "h": 0, "z": 0}
    for x in tab("_tab05f.csv"):
        k = (x["OBEC"].strip(), x["PC_HL"].strip())
        if k in kand:
            kand[k]["h"] += int(x.get("P_HL") or 0)
            if (x.get("KANDIDAT") or "").strip() == "1":
                kand[k]["z"] = 1
    obce: dict[str, list] = defaultdict(list)
    kody = {o["kod"] for o in OBCE}
    for (obec, _), v in kand.items():
        if obec in kody:
            obce[obec].append(v)
    out = {}
    for obec, zoz in obce.items():
        spolu = sum(v["h"] for v in zoz) or 1
        zoz.sort(key=lambda v: -v["h"])
        out[obec] = [[v["m"], v["s"], v["h"], round(100 * v["h"] / spolu, 1), v["z"]] for v in zoz[:6]]
    print(f"Starosta 2022: {len(out)} obcí, {len(kand)} kandidátov")
    if len(out) < 2500:
        raise RuntimeError(f"starosta 2022: len {len(out)} obcí")
    zapis_ak_zmena(DATA / "obce" / "starosta2022.json", {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                       "zdroj": {"nazov": "ŠÚ SR – voľby do orgánov samosprávy obcí 2022", "url": "https://volby.statistics.sk/oso/oso2022/"},
                                                       "polia": ["kandidát", "strana", "hlasy", "%", "zvolený"], "obce": dict(sorted(out.items()))}, kompaktne=True)


def main() -> int:
    try:
        starosta2022()
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Starosta 2022::{e}")
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
    stare_u = json.loads(stare_f.read_text(encoding="utf-8")).get("ucast", {}) if stare_f.exists() else {}
    ucast = {}
    for vid, nazov, url in UCAST:
        try:
            ucast[vid] = {"nazov": nazov, **len_ucast(url)}
            print(f"{nazov}: účasť SR {ucast[vid]['sr']} %, {len(ucast[vid]['obce'])} obcí")
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Účasť {vid}::{e}")
            if vid in stare_u:
                ucast[vid] = stare_u[vid]
    zapis_ak_zmena(stare_f, {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "zdroj": {"nazov": "ŠÚ SR – výsledky volieb, otvorené dáta", "url": "https://volby.statistics.sk"},
                             "volby": out, "ucast": ucast}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Voľby v obciach")
