"""Výsledky Testovania 9 podľa škôl (NIVAM, dataportal.nucem.sk) → data/obce/t9.json.

Dataportál je JSF formulár: pre každý predmet a kraj sa odošle formulár a z HTML tabuľky sa prečíta
názov školy, obec, ulica, počet testovaných (N) a priemerná úspešnosť školy (PÚŠ, %). Rozdiel od národného
priemeru (RNP) dataportál uvádza len pri školách s 16 a viac žiakmi; národný priemer = PÚŠ − RNP.

Škola sa priradí k obci podľa názvu obce v rámci kraja (pri zhode názvov v kraji sa nepriradí).
Ukladajú sa len údaje o školách (inštitúciách), nie o žiakoch.
"""

from __future__ import annotations

import html as H
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timezone

import requests

from spolocne import DATA, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE, kluc

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


def _cislo(t: str) -> float | None:
    t = t.strip().replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def tabulka(s: requests.Session, rok: int, predmet: str, kraj: str, typz: str = "", jazyk: str = "") -> list[dict]:
    u = ZAKLAD.format(rok=rok)
    h = s.get(u, timeout=60).text
    vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h).group(1)
    tl = re.search(r'<(?:button|input)[^>]*name="(j_idt10:[^"]+)"[^>]*(?:type="submit"|Vybra)', h) or re.search(r'name="(j_idt10:j_idt\d+)"[^>]*type="submit"', h)
    data = {"j_idt10": "j_idt10", "j_idt10:predmet_input": predmet, "j_idt10:kraj_input": kraj, "j_idt10:okres_input": "",
            "j_idt10:typz_input": typz, "j_idt10:zriadovatel_input": "", "j_idt10:language_input": jazyk, "javax.faces.ViewState": vs}
    data[tl.group(1) if tl else "j_idt10:j_idt29"] = "Vybrať"
    r = s.post(u, data=data,
               headers={"Referer": u, "Origin": "https://dataportal.nucem.sk"}, timeout=120)
    r.raise_for_status()
    texty = [r.text]
    # tabuľka je stránkovaná po 20 riadkoch (PrimeFaces DataTable) – zvyšok cez AJAX stránkovanie s veľkým počtom riadkov
    tab = re.search(r'<div id="([^"]+)" class="ui-datatable', r.text)
    vs2 = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', r.text)
    if tab and vs2:
        tid = tab.group(1)
        form = tid.split(":")[0]
        data2 = {"javax.faces.partial.ajax": "true", "javax.faces.source": tid, "javax.faces.partial.execute": tid,
                 "javax.faces.partial.render": tid, tid + "_pagination": "true", tid + "_first": "20", tid + "_rows": "5000",
                 tid + "_encodeFeature": "true", form: form, "javax.faces.ViewState": vs2.group(1)}
        r2 = s.post(u, data=data2, headers={"Referer": u, "Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest"}, timeout=180)
        if r2.ok:
            texty.append(r2.text)
    out = []
    videne = set()
    for txt in texty:
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", txt, flags=re.S):
            bunky = [H.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
            bunky = [re.sub(r"\s+", " ", c) for c in bunky]
            if len(bunky) < 12:
                continue
            # Názov | Obec | Ulica | Zriaďovateľ | Jazyk | N | N/ZZ | N/SZP | N/C | PZŠ | PÚŠ | RNP | Sig. | PŠ
            n, pus, rnp = _cislo(bunky[5]), _cislo(bunky[10]), _cislo(bunky[11])
            if n is None or pus is None or (bunky[0], bunky[1], bunky[2], bunky[4]) in videne:
                continue
            videne.add((bunky[0], bunky[1], bunky[2], bunky[4]))
            out.append({"nazov": bunky[0], "obec": bunky[1], "ulica": bunky[2], "n": int(n), "pus": pus, "rnp": rnp})
    return out


def main() -> int:
    s = relacia()
    rok = najnovsi_rok(s)
    skoly: dict[tuple[str, str, str], dict] = {}
    priemer: dict[str, list[float]] = defaultdict(list)
    nepr = set()
    for pk, p in PREDMETY.items():
        for kk, kraj in KRAJE.items():
            riadky = tabulka(s, rok, pk, kk)
            if pk == "55" and len(riadky) < 50:
                raise RuntimeError(f"T9 {rok}: {kraj} matematika len {len(riadky)} škôl")
            for x in riadky:
                kandid = V_KRAJI.get((kraj, kluc(x["obec"])), [])
                if len(kandid) != 1:
                    nepr.add((kraj, x["obec"]))
                    continue
                k = (kandid[0], x["nazov"], x["ulica"])
                sk = skoly.setdefault(k, {"nazov": x["nazov"], "ulica": x["ulica"]})
                sk[p] = [x["n"], round(x["pus"], 1)]
                if x["rnp"] is not None:
                    priemer[p].append(x["pus"] - x["rnp"])
    sr = {p: round(statistics.median(v), 1) for p, v in priemer.items() if v}
    obce: dict[str, list] = defaultdict(list)
    for (kod, _, _), v in sorted(skoly.items()):
        obce[kod].append(v)
    print(f"T9 {rok}: {len(skoly)} škôl v {len(obce)} obciach, nepriradených obcí {len(nepr)} {sorted(nepr)[:5]}, priemer SR {sr}")
    if len(obce) < 800 or "mat" not in sr:
        raise RuntimeError(f"T9: len {len(obce)} obcí")
    zapis_ak_zmena(DATA / "obce" / "t9.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rok": rok, "sr": sr,
        "zdroj": {"nazov": "NIVAM – Testovanie 9, výsledky škôl (dataportal.nucem.sk)", "url": "https://dataportal.nucem.sk/Dataportal-web/web/vysledky/index.xhtml"},
        "obce": dict(sorted(obce.items()))}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Obce – Testovanie 9 (NIVAM)")
