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
        # riadok Spolu/Spolu v kocke často chýba – rozloha = poľnohospodárska + nepoľnohospodárska pôda, inak súčet druhov
        sp = d.get((rok, "Spolu", "Spolu")) or (d.get((rok, "Spolu", "Poľnohospodárska pôda"), 0) + d.get((rok, "Spolu", "Nepoľnohospodárska pôda"), 0)) \
            or sum(v for k, v in d.items() if k[0] == rok and k[1] in UZEMIE)
        if not sp:
            continue
        p: dict[str, float] = defaultdict(float)
        for k, v in d.items():
            if k[0] == rok and k[1] in UZEMIE and v:
                p[UZEMIE[k[1]]] += 100 * v / sp
        p = {k: round(v, 1) for k, v in p.items()}
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


# ---------------- veková pyramída (aktuálny rok) ----------------

def _vek_skupina(n: str) -> tuple[int, bool] | None:
    """(index 5-ročnej skupiny 0–4 … 80–84, 85+ = 17; True ak je to otvorená skupina „N a viac“); iné skupiny None."""
    n = n.strip()
    if n == "4 roky alebo menej":
        return 0, False
    m = re.fullmatch(r"Od (\d+) do (\d+) rokov", n)
    if m and int(m.group(2)) - int(m.group(1)) == 4 and int(m.group(1)) % 5 == 0:
        return min(int(m.group(1)) // 5, 17), False
    m = re.fullmatch(r"(\d+) rokov alebo viac", n)
    if m and int(m.group(1)) == 85:
        return 17, True
    return None


def vek() -> None:
    surove: dict[str, dict[str, dict]] = {}  # obec -> pohlavie -> {(i, otvorena): hodnota}
    rok = None
    for x in riadky_obce("om7006rr", rokov=1, vyber={"e_sex": ["Muži", "Ženy"]}):
        if "31" not in (x.get("e_indic") or ""):  # stav k 31. 12. (nie k 30. 6.)
            continue
        sk = _vek_skupina(x.get("e_age") or "")
        v = cislo(x.get("hodnota"))
        kod = obec(x) if sk is not None and v is not None else None
        if not kod:
            continue
        rok = x["_cas"].strip()
        p = "m" if x["e_sex"].strip() == "Muži" else "z"
        d = surove.setdefault(kod, {"m": {}, "z": {}})[p]
        d[sk] = d.get(sk, 0) + int(v)
    out: dict[str, dict[str, list]] = {}
    for kod, d in surove.items():
        o = {}
        for p, h in d.items():
            a = [0] * 18
            for (i, otv), v in h.items():
                if i < 17:
                    a[i] += v
            # 85+: otvorená skupina, ak ju kocka má; inak súčet 85–89, 90–94, …
            a[17] = h.get((17, True), h.get((17, False), 0))
            o[p] = a
        if sum(o["m"]) + sum(o["z"]) > 0:
            out[kod] = o
    if len(out) < 2500:
        raise RuntimeError(f"vek: len {len(out)} obcí")
    zapis("vek", {"rok": rok, "skupiny": [f"{5 * i}–{5 * i + 4}" for i in range(17)] + ["85+"],
                  "zdroj": {"nazov": "ŠÚ SR – vekové skupiny obyvateľstva podľa pohlavia (STATdata om7006rr)", "url": "https://statdata.statistics.sk"},
                  "obce": dict(sorted(out.items()))})
    print(f"Vek {rok}: {len(out)} obcí")


# ---------------- počet obyvateľov mesačne ----------------

def mesacne() -> None:
    from datetime import date
    rok = date.today().year
    out: dict[str, dict[str, int]] = defaultdict(dict)
    for r in (rok, rok - 1):
        try:
            rr = riadky_obce("om7101mr", vyber={"e_sex": ["Spolu"], "e_year": [str(r)]})
        except Exception as e:  # noqa: BLE001 – rok ešte nemusí byť v kocke
            print(f"  om7101mr {r}: {e}")
            continue
        for x in rr:
            if "konci" not in (x.get("e_indic") or "").lower():  # stav na konci mesiaca
                continue
            v = cislo(x.get("hodnota"))
            kod = obec(x) if v is not None else None
            mes = re.sub(r"\D", "", x.get("e_month") or x.get("_cas") or "")
            if kod and mes:
                out[kod][f"{r}-{int(mes):02d}"] = int(v)
        if out:
            break
    obce = {k: sorted(d.items())[-1] for k, d in out.items() if d}
    if len(obce) < 2500:
        raise RuntimeError(f"mesačne: len {len(obce)} obcí")
    mes = max(m for m, _ in obce.values())
    zapis("mesacne", {"mesiac": mes, "zdroj": {"nazov": "ŠÚ SR – počet obyvateľov mesačne (STATdata om7101mr), stav na konci mesiaca", "url": "https://statdata.statistics.sk"},
                      "obce": {k: v[1] for k, v in sorted(obce.items()) if v[0] == mes}})
    print(f"Mesačne {mes}: {len(obce)} obcí")


# ---------------- domácnosti, byty, ekonomická aktivita, cudzinci (SODB 2021) ----------------

def _p(d: dict, k: str, zn: float) -> float | None:
    return round(100 * d.get(k, 0) / zn, 1) if zn else None


def sodb2() -> None:
    obce: dict[str, dict] = defaultdict(dict)
    dom = tabulka("om7822rr", "e_poc_clen_cd", "e_typcd", rokov=1)
    for kod, d in dom.items():
        c = {k[1]: v for k, v in d.items() if k[0] == "2021" and k[2] == "Spolu"}
        sp = c.get("Spolu")
        if sp:
            osob = sum(v * n for n, v in ((1, c.get("1-členná domácnosť", 0)), (2, c.get("2-členná domácnosť", 0)), (3, c.get("3-členná domácnosť", 0)),
                                          (4, c.get("4-členná domácnosť", 0)), (5.6, c.get("5 a viac členná domácnosť", 0))))
            obce[kod]["dom"] = {"n": int(sp), "jedn": _p(c, "1-členná domácnosť", sp), "velke": _p(c, "5 a viac členná domácnosť", sp), "priem": round(osob / sp, 2)}
    det = tabulka("om7823rr", "e_poc_deti", "e_typcd", rokov=1)
    for kod, d in det.items():
        c = {k[1]: v for k, v in d.items() if k[0] == "2021" and k[2] == "Spolu"}
        sp = c.get("Spolu")
        if sp and "dom" in obce.get(kod, {}):
            obce[kod]["dom"]["deti"] = round(100 * (sp - c.get("0 detí", 0)) / sp, 1)
    izby = tabulka("om7818rr", "e_nrooms", "e_buildtype", rokov=1)
    for kod, d in izby.items():
        c = {k[1]: v for k, v in d.items() if k[0] == "2021" and k[2] == "Spolu"}
        zn = c.get("Spolu", 0) - c.get("Nezistené", 0)
        if zn > 0:
            s_ = sum(v * int(re.match(r"\d+", k).group()) for k, v in c.items() if re.match(r"\d+", k))
            obce[kod].setdefault("byty", {})["izby"] = round(s_ / zn, 1)
    plocha = tabulka("om7820rr", "e_sqmetrs", "e_buildtype", rokov=1)
    STRED = [(r"menej ako 30", 25), (r"<30 m2 - 40", 35), (r"<40 m2 - 50", 45), (r"<50 m2 - 60", 55), (r"<60 m2 - 80", 70), (r"<80 m2 - 100", 90),
             (r"<100 m2 - 120", 110), (r"120 m2 - 150", 135), (r"<150 m2 a viac", 175)]
    for kod, d in plocha.items():
        c = {k[1]: v for k, v in d.items() if k[0] == "2021" and k[2] == "Spolu"}
        zn = c.get("Spolu", 0) - c.get("nezistená", 0)
        if zn > 0:
            s_ = sum(v * m for k, v in c.items() for vz, m in STRED if k.startswith(vz))
            obce[kod].setdefault("byty", {})["m2"] = round(s_ / zn)
    vl = tabulka("om7819rr", "e_ownerb", "e_buildtype", rokov=1)
    for kod, d in vl.items():
        c = {k[1]: v for k, v in d.items() if k[0] == "2021" and k[2] == "Spolu"}
        zn = c.get("Spolu", 0) - c.get("nezistený", 0)
        if zn > 0:
            vlastne = c.get("vlastný byt v bytovom dome", 0) + c.get("byt vo vlastnom rodinnom dome", 0)
            najom = c.get("byt v nájme", 0) + c.get("obecný byt", 0) + c.get("služobný a domovnícky byt", 0)
            obce[kod].setdefault("byty", {}).update({"vlastne": round(100 * vlastne / zn, 1), "najom": round(100 * najom / zn, 1),
                                                     "druzstvo": _p(c, "družstevný byt - len stavebné bytové družstvo", zn)})
    en = tabulka("om7817rr", "e_energy", "e_buildtype", rokov=1)
    for kod, d in en.items():
        c = {k[1]: v for k, v in d.items() if k[0] == "2021" and k[2] == "Spolu"}
        zn = c.get("Spolu", 0) - c.get("nezistený", 0)
        if zn > 0:
            obce[kod].setdefault("byty", {})["energia"] = {k: _p(c, n, zn) for k, n in (("plyn", "plyn"), ("elektrina", "elektrina"), ("pevne", "pevné palivo"),
                                                                                        ("kvapalne", "kvapalné palivo"), ("slnko", "solárna enregia"), ("iny", "iný"), ("ziadny", "žiadny"))}
    ek = tabulka("om7803rr", "e_wstatus", "e_sex", "e_age", rokov=1, vyber={"e_sex": ["Spolu"], "e_age": ["Spolu"]})
    for kod, d in ek.items():
        c = {k[1]: v for k, v in d.items() if k[0] == "2021"}
        sp = c.get("Spolu")
        if sp:
            obce[kod]["ekon"] = {"aktivni": _p(c, "Ekonomicky aktívny", sp), "nezam": _p(c, "Nezamestnaní", sp), "dochodcovia": _p(c, "Dôchodcovia", sp),
                                 "deti_studenti": _p(c, "Dieťa/študent", sp)}
    ci = tabulka("om7807rr", "e_country", "e_sex", "e_age", rokov=1, vyber={"e_sex": ["Spolu"], "e_age": ["Spolu"]})
    for kod, d in ci.items():
        c = {k[1]: v for k, v in d.items() if k[0] == "2021"}
        zn = c.get("Spolu", 0) - c.get("Nezistené", 0)
        if zn > 0:
            cud = c.get("Česká republika", 0) + c.get("Ostatné", 0) + c.get("Bez štátnej príslušnosti", 0)
            obce[kod]["cudzinci"] = [int(cud), round(100 * cud / zn, 1), int(c.get("Česká republika", 0))]
    zapis("sodb2", {"rok": 2021, "zdroj": {"nazov": "ŠÚ SR – Sčítanie 2021: domácnosti (om7822rr, om7823rr), byty (om7817–7820rr), ekonomická aktivita (om7803rr), štátna príslušnosť (om7807rr)",
                                         "url": "https://statdata.statistics.sk"},
                    "obce": dict(sorted(obce.items()))})
    print(f"SODB2: {len(obce)} obcí, domácnosti {sum('dom' in v for v in obce.values())}, byty {sum('byty' in v for v in obce.values())}, ekon {sum('ekon' in v for v in obce.values())}")


# ---------------- kultúra a voda ----------------

def kultura() -> None:
    obce: dict[str, dict] = defaultdict(dict)
    rok_k = None
    for kocka, mapa in (("ku5003rr", {"Počet stálych kín": "kino"}), ("ku5005rr", {"Počet galérií": "galeria", "Počet múzeí": "muzeum"}),
                        ("ku5006rr", {"Počet zariadení": "cvc"}), ("ku5011rr", {"Počet stálych scén a priestorov": "divadlo"})):
        rr = riadky_obce(kocka, rokov=2)
        roky = sorted({x["_cas"].strip() for x in rr if cislo(x.get("hodnota")) is not None})
        if not roky:
            continue
        rok = roky[-1]
        rok_k = max(rok_k or rok, rok)
        for x in rr:
            if x["_cas"].strip() != rok:
                continue
            k = mapa.get((x.get("e_indic") or "").strip())
            v = cislo(x.get("hodnota"))
            kod = obec(x) if k and v else None
            if kod and v > 0:
                obce[kod][k] = int(v)
    voda: dict[str, list] = {}
    rr = riadky_obce("vh5003rr", rokov=2)
    roky = sorted({x["_cas"].strip() for x in rr if cislo(x.get("hodnota")) is not None})
    rok_v = roky[-1] if roky else None
    for x in rr:
        if x["_cas"].strip() == rok_v and "domácnosti" in (x.get("e_indic") or ""):
            v = cislo(x.get("hodnota"))
            kod = obec(x) if v is not None else None
            if kod:
                voda[kod] = v
    zapis("kultura", {"rok": rok_k, "rok_voda": rok_v,
                      "zdroj": {"nazov": "ŠÚ SR – kiná (ku5003rr), múzeá a galérie (ku5005rr), centrá voľného času (ku5006rr), scénické umenie (ku5011rr), spotreba pitnej vody (vh5003rr)",
                                "url": "https://statdata.statistics.sk"},
                      "obce": dict(sorted(obce.items())), "voda": dict(sorted(voda.items()))})
    print(f"Kultúra {rok_k}: {len(obce)} obcí; voda {rok_v}: {len(voda)} obcí")


MODULY = {"pohyb": pohyb, "byvanie": byvanie, "firmy": firmy, "sluzby": sluzby, "turizmus": turizmus, "obyvatelia": obyvatelia, "uzemie": uzemie, "vek": vek, "mesacne": mesacne, "sodb2": sodb2, "kultura": kultura}


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
