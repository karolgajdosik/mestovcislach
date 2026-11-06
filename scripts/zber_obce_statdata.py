"""Údaje ŠÚ SR (STATdata) za všetky obce – kocky so zonáciou „Obce“.

  pohyb    – om7103rr pohyb obyvateľstva (narodení, zomrelí, prisťahovaní, vysťahovaní; ročne)
             om7052rr indexy vekového zloženia (priemerný vek, index starnutia)
  byvanie  – SODB 2021: om7811rr kanalizácia, om7815rr plyn, om7816rr vodovod (domy),
             om7813rr obdobie výstavby (domy), om7821rr typ kúrenia (byty)
  firmy    – og3805rr právnické osoby, og3808rr fyzické osoby – podnikatelia (len počty)
  sluzby   – zd5001rr zdravotnícke zariadenia (ambulancie, lekárne), ik5001rr pošty, ku5008rr verejné knižnice
  obyvatelia – SODB 2021: om7809rr vzdelanie, om7806rr národnosť, om7804rr materinský jazyk, om7805rr náboženstvo
             (len súhrnné podiely; skupiny pod 5 osôb sa zlúčia do „iné“)
  uzemie   – pl5001rr výmera a využitie pôdy (orná pôda, lesy, zastavané plochy …)
  turizmus – cr3805qr ubytovacie zariadenia (kapacity, návštevníci; ŠÚ SR zverejňuje len obce, kde to dovolí
             ochrana dôverných údajov)

Výstupy: data/obce/<modul>.json. Moduly bežia samostatne: python scripts/zber_obce_statdata.py pohyb byvanie …
"""

from __future__ import annotations

import sys
import re
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, spusti, zapis_ak_zmena
from statdata_obce import riadky_obce
from zber_obce_temy import OBCE, cislo, median, najdi_obec

OKRES = {o["kod"]: o["okres"] for o in OBCE}


def obec(x: dict) -> str | None:
    n = (x.get("e_nuts15") or "").strip()
    okres = (x.get("e_nuts14") or "").strip().removeprefix("Okres ").strip() or None
    if "," in n and "okres" in n:
        n, okres = [t.strip() for t in n.split(", okres", 1)]
    return najdi_obec(n, okres)


def tabulka(kocka: str, *dims: str, filtr=None, rokov: int | None = None, vyber: dict | None = None) -> dict[str, dict[tuple, float]]:
    """{kód obce: {(čas, dim1, dim2 …): hodnota}} – prázdne hodnoty („.“) a duplicity z kontextu sa vynechajú."""
    out: dict[str, dict[tuple, float]] = defaultdict(dict)
    nenajdene = set()
    for x in riadky_obce(kocka, rokov, vyber):
        if filtr and not filtr(x):
            continue
        v = cislo(x.get("hodnota"))
        if v is None:
            continue
        kod = obec(x)
        if not kod:
            nenajdene.add(x.get("e_nuts15", "").strip())
            continue
        k = (x["_cas"].strip(),) + tuple((x.get(d) or "").strip() for d in dims)
        out[kod].setdefault(k, v)
    print(f"  {kocka}: {len(out)} obcí, nepriradených území {len(nenajdene)}")
    if len(out) < 2000:
        raise RuntimeError(f"{kocka}: priradených len {len(out)} obcí (napr. {sorted(nenajdene)[:6]})")
    return out


def zapis(nazov: str, obsah: dict) -> None:
    zapis_ak_zmena(DATA / "obce" / f"{nazov}.json", {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), **obsah}, kompaktne=True)


def okresne_mediany(obce: dict[str, dict], polia: list[str]) -> dict:
    po: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for kod, v in obce.items():
        for p in polia:
            if v.get(p) is not None:
                po[OKRES[kod]][p].append(v[p])
    return {o: {p: (round(m, 1) if (m := median(xs)) is not None else None) for p, xs in d.items()} for o, d in sorted(po.items())}


# ---------------- pohyb obyvateľstva ----------------

POHYB_KL = {"živonarodení": "nar", "narodení": "nar", "živonarodené deti": "nar", "zomretí": "zom", "zomrelí": "zom",
            "celkový prírastok obyvateľstva": "cel"}


def pohyb_kluc(ind: str) -> str | None:
    return POHYB_KL.get(re.sub(r"\s+", " ", ind).strip().lower())


def pohyb() -> None:
    vsetky_ind: set[str] = set()

    def f(x: dict) -> bool:
        vsetky_ind.add(x.get("e_indic", "").strip())
        return pohyb_kluc(x.get("e_indic", "")) is not None
    t = tabulka("om7103rr", "e_indic", rokov=10, filtr=f)
    najdene = {pohyb_kluc(i) for i in vsetky_ind} - {None}
    if not {"nar", "zom", "cel"} <= najdene:
        print(f"::warning title=Pohyb obyvateľstva::nenájdené ukazovatele {set(POHYB_KL.values()) - najdene}; v kocke: {sorted(vsetky_ind)}")
    obce: dict[str, dict] = {}
    roky_vsetky = sorted({k[0] for v in t.values() for k in v})
    roky = roky_vsetky[-10:]
    for kod, d in t.items():
        rad = {}
        for r in roky:
            z = {pohyb_kluc(k[1]): int(v) for k, v in d.items() if k[0] == r}
            if {"nar", "zom", "cel"} <= set(z):  # saldo sťahovania = celkový prírastok − prirodzený prírastok
                rad[r] = [z["nar"], z["zom"], z["cel"] - (z["nar"] - z["zom"])]
        if rad:
            obce[kod] = {"rad": rad}
    vek = tabulka("om7052rr", "e_indic", "e_sex", rokov=11, filtr=lambda x: x.get("e_sex", "").strip() == "Spolu")
    for kod, d in vek.items():
        rok = max(k[0] for k in d)
        pv = d.get((rok, "Priemerný vek obyvateľa", "Spolu"))
        ist = d.get((rok, "Index starnutia", "Spolu"))
        if kod in obce or pv is not None:
            obce.setdefault(kod, {})
            if pv is not None:
                obce[kod]["vek"] = round(pv, 1)
                obce[kod]["vek_rok"] = rok
                pv10 = d.get((str(int(rok) - 10), "Priemerný vek obyvateľa", "Spolu"))
                if pv10 is not None:
                    obce[kod]["vek10"] = round(pv10, 1)
            if ist is not None:
                obce[kod]["starnutie"] = round(ist)
    zapis("pohyb", {"roky": roky, "okresy": okresne_mediany(obce, ["vek"]),
                    "zdroj": {"nazov": "ŠÚ SR – pohyb obyvateľstva (om7103rr), indexy vekového zloženia (om7052rr)", "url": "https://statdata.statistics.sk"},
                    "obce": dict(sorted(obce.items()))})
    print(f"Pohyb: {len(obce)} obcí, roky {roky[0]}–{roky[-1]}")


# ---------------- bývanie (SODB 2021) ----------------

def podiely(t: dict[str, dict[tuple, float]], dim_hodnoty: dict[str, str], spolu: str = "Spolu") -> dict[str, dict[str, float]]:
    """Podiel kategórií na domoch so zisteným údajom (Spolu mínus „nezistené“; typ domu Spolu, rok 2021).

    Pri sčítaní 2021 je pri časti domov údaj nezistený – podiel z celku by vybavenosť podhodnotil."""
    out = {}
    for kod, d in t.items():
        sp = d.get(("2021", "Spolu", spolu))
        if not sp:
            continue
        nez = sum(v for k, v in d.items() if k[0] == "2021" and k[1] == "Spolu" and k[2].lower().startswith("nezisten"))
        zn = sp - nez
        if zn < max(5, 0.5 * sp):  # pri väčšine domov nezistené – údaj nemá výpovednú hodnotu
            continue
        out[kod] = {k: round(100 * sum(d.get(("2021", "Spolu", h), 0) for h in hodn.split("|")) / zn, 1) for k, hodn in dim_hodnoty.items()}
        out[kod]["_n"] = int(sp)
        out[kod]["_zn"] = zn
    return out


def okresne_vazene(zdroje: dict[str, dict[str, dict]]) -> dict:
    """Podiel za okres zo súčtu domov (nie medián obcí): {okres: {pole: %}}."""
    acc: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    for pole, src in zdroje.items():
        for kod, v in src.items():
            if v.get(pole) is not None:
                a = acc[OKRES[kod]][pole]
                a[0] += v[pole] * v["_zn"]
                a[1] += v["_zn"]
    return {o: {p: round(a / b, 1) for p, (a, b) in d.items() if b} for o, d in sorted(acc.items())}


def byvanie() -> None:
    f = lambda x: x.get("e_year", "").strip() == "2021" and x.get("e_buildtype", "").strip() == "Spolu"  # noqa: E731
    kan = podiely(tabulka("om7811rr", "e_buildtype", "e_canal", filtr=f),
                  {"kanal": "prípojka na kanalizačnú sieť", "zumpa": "septik, žumpa", "cov": "domáca čistička odpadových vôd", "bez": "bez odkanalizovania"})
    plyn = podiely(tabulka("om7815rr", "e_buildtype", "e_gas", filtr=f), {"plyn": "plynová prípojka"})
    voda = podiely(tabulka("om7816rr", "e_buildtype", "e_watsup", filtr=f),
                   {"vodovod": "v dome - z verejnej siete|mimo domu - z verejnej siete", "studna": "v dome - vlastná|mimo domu - vlastná"})
    vek = podiely(tabulka("om7813rr", "e_buildtype", "e_periodconren", filtr=f),
                  {"do1945": "do roku 1945", "1946": "1946 - 1980", "1981": "1981 - 2000", "2001": "2001 - 2009", "2010": "2010 a neskôr"})
    kur = podiely(tabulka("om7821rr", "e_buildtype", "e_heat", filtr=f),
                  {"dialkove": "Ústredné kúrenie diaľkové", "ustredne": "Ústredné kúrenie lokálne", "etazove": "Etážové kúrenie", "teleso": "Samostatné vykurovacie teleso"})
    obce = {}
    for kod in set(kan) | set(plyn) | set(voda):
        o: dict = {}
        if kod in kan:
            o.update({k: v for k, v in kan[kod].items() if not k.startswith("_")})
            o["domov"] = kan[kod]["_n"]
        for zdroj in (plyn, voda):
            o.update({k: v for k, v in zdroj.get(kod, {}).items() if not k.startswith("_")})
        if kod in vek:
            o["vek_domov"] = [vek[kod][k] for k in ("do1945", "1946", "1981", "2001", "2010")]
        if kod in kur:
            o["kurenie"] = [kur[kod][k] for k in ("dialkove", "ustredne", "etazove", "teleso")]
            o["bytov"] = kur[kod]["_n"]
        obce[kod] = o
    zapis("byvanie", {"rok": "2021", "okresy": okresne_vazene({"kanal": kan, "plyn": plyn, "vodovod": voda}),
                      "zdroj": {"nazov": "ŠÚ SR – Sčítanie obyvateľov, domov a bytov 2021 (om7811rr, om7813rr, om7815rr, om7816rr, om7821rr)", "url": "https://statdata.statistics.sk"},
                      "obce": dict(sorted(obce.items()))})
    print(f"Bývanie: {len(obce)} obcí")


# ---------------- firmy ----------------

def firmy() -> None:
    po = tabulka("og3805rr", "e_legal_forms", rokov=11)
    fo = tabulka("og3808rr", "e_legal_forms", rokov=11)
    roky = sorted({k[0] for v in po.values() for k in v})[-11:]
    obce = {}
    for kod in set(po) | set(fo):
        rad = {}
        for r in roky:
            a = po.get(kod, {})
            b = fo.get(kod, {})
            if (r, "Právnické osoby spolu") in a or (r, "Spolu") in b:
                rad[r] = [int(a.get((r, "Právnické osoby ziskové"), 0)), int(a.get((r, "Právnické osoby neziskové"), 0)),
                          int(b.get((r, "Živnostníci"), 0)), int(b.get((r, "Spolu"), 0) - b.get((r, "Živnostníci"), 0))]
        if rad:
            obce[kod] = rad
    zapis("firmy", {"roky": roky, "polia": ["firmy (ziskové PO)", "neziskové PO", "živnostníci", "ostatné FO-podnikatelia"],
                    "zdroj": {"nazov": "ŠÚ SR – Register organizácií: právnické osoby (og3805rr) a fyzické osoby – podnikatelia (og3808rr) k 31. 12.", "url": "https://statdata.statistics.sk"},
                    "obce": dict(sorted(obce.items()))})
    print(f"Firmy: {len(obce)} obcí, roky {roky[0]}–{roky[-1]}")


# ---------------- služby (zdravotníctvo, pošta, knižnica) ----------------

ZDRAVIE = {
    "Samostatné ambulancie praktického lekára pre dospelých": "vseob", "Samostatné ambulancie praktického lekára pre deti": "deti",
    "Samostatné ambulancie praktického lekára stomatológa": "zubar", "Samostatné ambulancie praktického lekára gynekológa": "gyn",
    "Samostatné ambulancie lekára špecialistu": "spec", "Lekárne a výdajne liekov": "lekarne", "Nemocnice všeobecné a špecializované": "nemocnice",
    "Polikliniky samostatné (územné a podnikové)": "polikliniky", "Rýchla zdravotnícka pomoc": "rzp",
}


def sluzby() -> None:
    zd = tabulka("zd5001rr", "e_icha_hp", rokov=1)
    rok_zd = max(k[0] for v in zd.values() for k in v)
    obce: dict[str, dict] = defaultdict(dict)
    for kod, d in zd.items():
        z = {ZDRAVIE[i]: int(v) for (r, i), v in d.items() if r == rok_zd and i in ZDRAVIE and v > 0}
        if z:
            obce[kod]["zdravie"] = z
    try:
        po = tabulka("ik5001rr", rokov=1)
        rok_po = max(k[0] for v in po.values() for k in v)
        for kod, d in po.items():
            if d.get((rok_po,), 0) > 0:
                obce[kod]["posta"] = int(d[(rok_po,)])
    except Exception as e:  # noqa: BLE001
        rok_po = None
        print(f"::warning title=Pošty::{e}")
    try:
        kn = tabulka("ku5008rr", "e_indic", "e_libccat_libtype", rokov=1, filtr=lambda x: x.get("e_libccat_libtype", "").strip() == "Verejné knižnice")
        rok_kn = max(k[0] for v in kn.values() for k in v)
        for kod, d in kn.items():
            n = d.get((rok_kn, "Počet knižníc", "Verejné knižnice"), 0)
            if n > 0:
                obce[kod]["kniznica"] = [int(n), int(d.get((rok_kn, "Počet knižničných jednotiek", "Verejné knižnice"), 0))]
    except Exception as e:  # noqa: BLE001
        rok_kn = None
        print(f"::warning title=Knižnice::{e}")
    zapis("sluzby", {"roky": {"zdravie": rok_zd, "posta": rok_po, "kniznica": rok_kn},
                     "zdroj": {"nazov": "ŠÚ SR – zdravotníctvo (zd5001rr), pošty (ik5001rr), knižnice (ku5008rr) za obce", "url": "https://statdata.statistics.sk"},
                     "obce": dict(sorted(obce.items()))})
    print(f"Služby: {len(obce)} obcí, zdravotníctvo {rok_zd}")


# ---------------- cestovný ruch ----------------

TURIZMUS = {"Celkový počet ubytovacích zariadení k dispozícii": "zariadeni", "Celkový počet lôžok (vrátane kempingových miest) k dispozícii": "lozok",
            "Čisté využitie stálych lôžok v ubytovacích zariadeniach": "vyuzitie", "Tržby za ubytovanie spolu": "trzby"}


def turizmus() -> None:
    out: dict[str, dict[tuple, float]] = defaultdict(dict)
    for x in riadky_obce("cr3805qr"):
        if x.get("_cas", "").strip() != "1. - 4. Q." or (x.get("e_indic") or "").strip() not in TURIZMUS:
            continue
        v = cislo(x.get("hodnota"))
        kod = obec(x) if v is not None else None
        if kod:
            out[kod].setdefault(((x.get("e_year") or "").strip(), TURIZMUS[x["e_indic"].strip()]), v)
    if len(out) < 200:
        raise RuntimeError(f"Turizmus: len {len(out)} obcí")
    roky_vsetky = sorted({k[0] for v in out.values() for k in v})
    obce = {}
    for kod, d in out.items():
        rad = {r: {p: (round(v, 1) if p == "vyuzitie" else int(v)) for (rr, p), v in d.items() if rr == r} for r in roky_vsetky}
        rad = {r: v for r, v in rad.items() if v.get("zariadeni")}
        if rad:
            obce[kod] = rad
    zapis("turizmus", {"zdroj": {"nazov": "ŠÚ SR – Návštevnosť, tržby a kapacity ubytovacích zariadení (cr3805qr)", "url": "https://statdata.statistics.sk"},
                       "obce": dict(sorted(obce.items()))})
    print(f"Turizmus: {len(obce)} obcí, roky {roky_vsetky[0]}–{roky_vsetky[-1]}")


# ---------------- obyvatelia podľa SODB 2021: vzdelanie, národnosť, jazyk, náboženstvo ----------------

SPOLU = {"e_sex": ["Spolu"], "e_age": ["Spolu"]}
MALE = 5  # skupiny s menej ako 5 osobami v obci sa zlúčia do „iné“ (súhrnné údaje, ochrana malých počtov)


def _sodb(kocka: str, dim: str) -> dict[str, dict[str, float]]:
    t = tabulka(kocka, dim, rokov=1, vyber=SPOLU)
    return {kod: {k[1]: v for k, v in d.items() if k[0] == "2021"} for kod, d in t.items()}


def _skupiny(d: dict[str, float], vynechaj: set[str], ine: str) -> tuple[list, float]:
    """Podiely kategórií zo zistených údajov; malé skupiny do „iné“. Vráti ([[názov, %], …], počet zistených)."""
    zn = d.get("Spolu", 0) - sum(v for k, v in d.items() if k.lower().startswith("nezisten"))
    if zn <= 0:
        return [], 0
    pol, zvysok = [], 0.0
    for k, v in sorted(d.items(), key=lambda x: -x[1]):
        if k == "Spolu" or k in vynechaj or k.lower().startswith("nezisten") or v <= 0:
            continue
        if v < MALE or k == ine:
            zvysok += v
        else:
            pol.append([k, round(100 * v / zn, 1)])
    if zvysok:
        pol.append([ine, round(100 * zvysok / zn, 1)])
    return pol, zn


def _okres_podiely(po_obciach: dict[str, dict[str, float]], vynechaj: set[str]) -> dict:
    acc: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for kod, d in po_obciach.items():
        for k, v in d.items():
            acc[OKRES[kod]][k] += v
    out = {}
    for o, d in acc.items():
        zn = d.get("Spolu", 0) - sum(v for k, v in d.items() if k.lower().startswith("nezisten"))
        if zn > 0:
            out[o] = {k: round(100 * v / zn, 1) for k, v in d.items() if k != "Spolu" and k not in vynechaj and not k.lower().startswith("nezisten")}
    return dict(sorted(out.items()))


def _cirkev(n: str) -> str:
    m = re.search(r"\(([^)]+)\)", n)
    return m.group(1) if m and n not in ("Spolu",) else n


VZD = {"Základné vzdelanie": "zakl", "Základné": "zakl", "Stredné bez maturity": "sbm", "Stredné s maturitou": "sm", "Vysokoškolské": "vs",
       "Bez školského vzdelania - osoby vo veku 15 rokov a viac": "bez"}


def obyvatelia() -> None:
    vzd = _sodb("om7809rr", "e_edu")
    nar = _sodb("om7806rr", "e_national")
    jaz = _sodb("om7804rr", "e_language")
    nab = _sodb("om7805rr", "e_religion")
    deti = {k for d in vzd.values() for k in d if k.startswith("Bez ukončeného")}
    obce: dict[str, dict] = {}
    for kod, d in vzd.items():
        d = dict(d)
        for k in deti:
            d["Spolu"] = d.get("Spolu", 0) - d.pop(k, 0)  # deti do 14 rokov sa do vzdelania nerátajú
        zn = d.get("Spolu", 0) - sum(v for k, v in d.items() if k.lower().startswith("nezisten"))
        if zn >= 20:
            obce.setdefault(kod, {})["vzd"] = {VZD.get(k, k): round(100 * v / zn, 1) for k, v in d.items() if k in VZD}
            obce[kod]["vzd_n"] = int(zn)
    for src in (nab,):  # skrátené názvy cirkví („Rímskokatolícka cirkev v Slovenskej republike (rímskokatolícke) / …“ -> „rímskokatolícke“)
        for kod, d in src.items():
            src[kod] = {_cirkev(k): v for k, v in d.items()}
    for kluc, src, ine in (("nar", nar, "Iná"), ("jaz", jaz, "Iný jazyk"), ("nab", nab, "ostatné")):
        for kod, d in src.items():
            pol, zn = _skupiny(d, set(), ine)
            if pol and zn >= 20:
                obce.setdefault(kod, {})[kluc] = pol
    vzd_ok = {kod: {VZD.get(k, k) if k in VZD else k: v for k, v in d.items() if k in VZD or k == "Spolu" or k.lower().startswith("nezisten")}
              for kod, d in vzd.items()}
    for kod, d in vzd_ok.items():
        d["Spolu"] = vzd[kod].get("Spolu", 0) - sum(vzd[kod].get(k, 0) for k in deti)
    zapis("obyvatelia", {"rok": 2021, "male": MALE,
                         "okresy": {"vzd": _okres_podiely(vzd_ok, set()), "nar": _okres_podiely(nar, set()), "nab": _okres_podiely(nab, set())},
                         "zdroj": {"nazov": "ŠÚ SR – Sčítanie obyvateľov, domov a bytov 2021 (om7809rr vzdelanie, om7806rr národnosť, om7804rr materinský jazyk, om7805rr náboženské vyznanie)",
                                   "url": "https://statdata.statistics.sk"},
                         "obce": dict(sorted(obce.items()))})
    print(f"Obyvatelia SODB: {len(obce)} obcí, so vzdelaním {sum(1 for v in obce.values() if 'vzd' in v)}, národnosťou {sum(1 for v in obce.values() if 'nar' in v)}")


# ---------------- využitie územia ----------------

UZEMIE = {"Orná pôda": "orna", "Trvalé trávne porasty": "ttp", "Lesné pozemky": "les", "Vodné plochy": "voda",
          "Zastavané plochy a nádvoria": "zast", "Domáce záhradky": "zahr", "Vinohrady": "vin", "Ovocné sady": "sad",
          "Chmeľnice": "chmel", "Chmeľnica": "chmel", "Ostatné pôdne plochy": "ost"}


def uzemie() -> None:
    t = tabulka("pl5001rr", "e_landuse", "e_soiltype", rokov=1)
    obce = {}
    rok = None
    for kod, d in t.items():
        rok = max(k[0] for k in d)
        sp = d.get((rok, "Spolu", "Spolu"))
        if not sp:
            continue
        p = {UZEMIE[k[1]]: round(100 * v / sp, 1) for k, v in d.items() if k[0] == rok and k[1] in UZEMIE and v}
        obce[kod] = {"ha": round(sp / 10000), "p": p}
    okr: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for kod, v in obce.items():
        for k, pct in v["p"].items():
            okr[OKRES[kod]][k] += pct * v["ha"]
        okr[OKRES[kod]]["_ha"] += v["ha"]
    okresy = {o: {k: round(x / d["_ha"], 1) for k, x in d.items() if k != "_ha"} for o, d in sorted(okr.items()) if d["_ha"]}
    zapis("uzemie", {"rok": rok, "okresy": okresy,
                     "zdroj": {"nazov": "ŠÚ SR – Výmera územia, využitie pôdy (pl5001rr, podľa katastra nehnuteľností)", "url": "https://statdata.statistics.sk"},
                     "obce": dict(sorted(obce.items()))})
    print(f"Územie {rok}: {len(obce)} obcí")


MODULY = {"pohyb": pohyb, "byvanie": byvanie, "firmy": firmy, "sluzby": sluzby, "turizmus": turizmus, "obyvatelia": obyvatelia, "uzemie": uzemie}


def main() -> int:
    vyber = sys.argv[1:] or list(MODULY)
    chyby = 0
    for m in vyber:
        try:
            MODULY[m]()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=Obce STATdata – {m}::{e}")
    if chyby == len(vyber):
        raise RuntimeError("žiadny modul neprebehol")
    return 0


if __name__ == "__main__":
    spusti(main, "Obce – údaje ŠÚ SR (STATdata)")
