"""Výsledky Testovania 9 podľa škôl (NIVAM, dataportal.nucem.sk) → data/obce/t9.json.

Dataportál ponúka „databázy výsledkov v .xls“ za každý predmet (JSF odkaz – POST formulára j_idt35 s ViewState):
kód školy, názov, ulica, obec, N (počet testovaných), … , uspes (priemerná úspešnosť školy, %).
HTML tabuľka je stránkovaná po 20 riadkoch a AJAX stránkovanie z mimo prehliadača nefunguje – preto xls.

Škola sa priradí k obci podľa názvu obce; obce s rovnakým názvom vo viacerých okresoch sa preskočia.
Priemer SR = vážený priemer škôl podľa počtu žiakov. Ukladajú sa len údaje o školách (inštitúciách).
"""

from __future__ import annotations

import html as H
import re
from collections import defaultdict
from datetime import date, datetime, timezone

import requests

from spolocne import DATA, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE, PODLA_NAZVU, kluc

ZAKLAD = "https://dataportal.nucem.sk/Dataportal-web/web/vysledky/{rok}/testovanie/index.xhtml"
PREDMETY = {"55": "mat", "51": "sjl", "53": "mjl"}
KRAJE = {"1": "Bratislavský kraj", "2": "Trnavský kraj", "3": "Trenčiansky kraj", "4": "Nitriansky kraj",
         "5": "Žilinský kraj", "6": "Banskobystrický kraj", "7": "Prešovský kraj", "8": "Košický kraj"}

V_KRAJI: dict[tuple[str, str], list[str]] = defaultdict(list)
for _o in OBCE:
    V_KRAJI[(_o["kraj"], kluc(_o["nazov"]))].append(_o["kod"])


def relacia() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; mestovcislach.sk; info@mestovcislach.sk)",
                      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "sk"})
    return s


def najnovsi_rok(s: requests.Session) -> int:
    for r in range(date.today().year, date.today().year - 4, -1):
        try:
            x = s.get(ZAKLAD.format(rok=r), timeout=60)
            if x.status_code == 200 and "ViewState" in x.text:
                return r
        except requests.RequestException:
            pass
    raise RuntimeError("dataportál NÚCEM: žiadny rok s výsledkami")


def _cislo(t) -> float | None:
    try:
        return float(str(t).strip().replace(",", "."))
    except ValueError:
        return None


PREDMET_NAZOV = {"Matematika": "mat", "Slovenský jazyk a literatúra": "sjl", "Maďarský jazyk a literatúra": "mjl"}


def xls(s: requests.Session, rok: int) -> dict[str, list[dict]]:
    import xlrd
    u = ZAKLAD.format(rok=rok)
    h = s.get(u, timeout=60).text
    vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h).group(1)
    out = {}
    for lid, nazov in re.findall(r"'j_idt35:(j_idt\d+)':'j_idt35:j_idt\d+'\},''\);return false\">([^<]*)<", h):
        p = PREDMET_NAZOV.get(nazov.strip())
        if not p:
            continue
        r = s.post(u, data={"j_idt35": "j_idt35", f"j_idt35:{lid}": f"j_idt35:{lid}", "javax.faces.ViewState": vs}, headers={"Referer": u}, timeout=300)
        r.raise_for_status()
        sh = xlrd.open_workbook(file_contents=r.content).sheet_by_index(0)
        hl = [str(x).strip() for x in sh.row_values(0)]
        riadky = []
        for i in range(1, sh.nrows):
            d = dict(zip(hl, sh.row_values(i)))
            n, us = _cislo(d.get("N")), _cislo(d.get("uspes"))
            if n and us is not None:
                riadky.append({"nazov": str(d.get("nazov", "")).strip(), "ulica": str(d.get("ulica_cislo", "")).strip(),
                               "obec": str(d.get("obec", "")).strip(), "n": int(n), "pus": us})
        out[p] = riadky
    return out


def main() -> int:
    s = relacia()
    rok = najnovsi_rok(s)
    data = xls(s, rok)
    if len(data.get("mat", [])) < 1000:
        raise RuntimeError(f"T9 {rok}: matematika len {len(data.get('mat', []))} škôl")
    skoly: dict[tuple[str, str, str], dict] = {}
    sr = {}
    nepr = set()
    for p, riadky in data.items():
        sr[p] = round(sum(x["pus"] * x["n"] for x in riadky) / max(1, sum(x["n"] for x in riadky)), 1)
        for x in riadky:
            kandid = PODLA_NAZVU.get(kluc(x["obec"]), []) or PODLA_NAZVU.get(kluc(re.split(r"\s*-\s*", x["obec"])[0]), [])
            if len(kandid) != 1:
                nepr.add(x["obec"])
                continue
            k = (kandid[0], x["nazov"], x["ulica"])
            sk = skoly.setdefault(k, {"nazov": x["nazov"], "ulica": x["ulica"]})
            sk[p] = [x["n"], round(x["pus"], 1)]
    obce: dict[str, list] = defaultdict(list)
    for (kod, _, _), v in sorted(skoly.items()):
        obce[kod].append(v)
    print(f"T9 {rok}: {len(skoly)} škôl v {len(obce)} obciach, nepriradené obce {len(nepr)} {sorted(nepr)[:8]}, priemer SR {sr}")
    if len(obce) < 800:
        raise RuntimeError(f"T9: len {len(obce)} obcí")
    zapis_ak_zmena(DATA / "obce" / "t9.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rok": rok, "sr": sr,
        "zdroj": {"nazov": "NIVAM – Testovanie 9, výsledky škôl (dataportal.nucem.sk)", "url": "https://dataportal.nucem.sk/Dataportal-web/web/vysledky/index.xhtml"},
        "obce": dict(sorted(obce.items()))}, kompaktne=True)
    return 0


MAT_PREDMETY = {"Slovenský jazyk a literatúra": "sjl", "Maďarský jazyk a literatúra": "mjl", "Anglický jazyk úroveň B2": "anj", "Matematika": "mat"}


def maturita(s: requests.Session) -> None:
    """Externá časť maturity podľa stredných škôl (xls databázy dataportálu, rovnaký postup ako T9) → maturita.json.
    Dataportál uvádza len typ školy (Gymnázium, SOŠ…), mesto a ulicu – nie celý názov."""
    import xlrd
    rok = None
    for r in range(date.today().year, date.today().year - 3, -1):
        x = s.get(ZAKLAD.format(rok=r).replace("/testovanie/", "/maturita/"), timeout=60)
        if x.status_code == 200 and "ViewState" in x.text:
            rok, h = r, x.text
            break
    if not rok:
        raise RuntimeError("maturita: žiadny rok")
    u = ZAKLAD.format(rok=rok).replace("/testovanie/", "/maturita/")
    vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h).group(1)
    skoly: dict[tuple, dict] = {}
    sr: dict[str, float] = {}
    for form, lid, nazov in re.findall(r"'(j_idt\d+):(j_idt\d+)':'j_idt\d+:j_idt\d+'\},''\);return false\">([^<]*)<", h):
        p = MAT_PREDMETY.get(nazov.strip())
        if not p:
            continue
        r = s.post(u, data={form: form, f"{form}:{lid}": f"{form}:{lid}", "javax.faces.ViewState": vs}, headers={"Referer": u}, timeout=300)
        r.raise_for_status()
        sh = xlrd.open_workbook(file_contents=r.content).sheet_by_index(0)
        hl = [str(c).strip() for c in sh.row_values(0)]
        sum_n = sum_u = 0.0
        for i in range(1, sh.nrows):
            d = dict(zip(hl, sh.row_values(i)))
            n, us = _cislo(d.get("N")), _cislo(d.get("uspes"))
            if not n or us is None:
                continue
            sum_n += n
            sum_u += n * us
            mesto = str(d.get("Mesto", "")).strip()
            kand = PODLA_NAZVU.get(kluc(mesto), []) or PODLA_NAZVU.get(kluc(re.split(r"\s*-\s*", mesto)[0]), [])
            if len(kand) != 1:
                continue
            k = (kand[0], str(d.get("skola", "")).split(".")[0])
            sk = skoly.setdefault(k, {"typ": str(d.get("Nazov", "")).strip(), "ulica": str(d.get("Ulica", "")).strip()})
            sk[p] = [int(n), round(us, 1)]
        if sum_n:
            sr[p] = round(sum_u / sum_n, 1)
    obce: dict[str, list] = defaultdict(list)
    for (kod, _), v in sorted(skoly.items()):
        obce[kod].append(v)
    print(f"Maturita {rok}: {len(skoly)} škôl v {len(obce)} obciach, priemer SR {sr}")
    if len(obce) < 100:
        raise RuntimeError(f"maturita: len {len(obce)} obcí")
    zapis_ak_zmena(DATA / "obce" / "maturita.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rok": rok, "sr": sr,
        "zdroj": {"nazov": "NIVAM – externá časť maturitnej skúšky, výsledky škôl (dataportal.nucem.sk)", "url": "https://dataportal.nucem.sk/Dataportal-web/web/vysledky/index.xhtml"},
        "obce": dict(sorted(obce.items()))}, kompaktne=True)


def oboje() -> int:
    chyby = 0
    for f in (main, lambda: maturita(relacia())):
        try:
            f()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=NIVAM::{e}")
    if chyby == 2:
        raise RuntimeError("T9 ani maturita neprebehli")
    return 0


if __name__ == "__main__":
    spusti(oboje, "Obce – Testovanie 9 a maturita (NIVAM)")
