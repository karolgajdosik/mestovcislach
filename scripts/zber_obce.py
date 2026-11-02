"""Všetky obce a mestá Slovenska – údaje pre stránky /<kraj>/<okres>/<obec>/ a úvodný filter.

Zdroje:
  - zoznam obcí s krajom a okresom + komunálne voľby 2026: balík ŠÚ SR OSO2026 (volbysr.sk, XLSX) – tab0d územie,
    tab0a/tab05 starosta (primátor), tab0b/tab08 poslanci, tab02b účasť
  - počet obyvateľov: STATdata om7101rr (stav k 1. 1. → rok −1 = stav k 31. 12.)
  - sčítanie 2021: STATdata om7803rr (vek), om7809rr (vzdelanie), om7806rr (národnosť), om7805rr (náboženstvo)
  - poloha obce (stred) a hranice krajov a okresov pre mapu: OpenStreetMap (Overpass), ODbL
Mestské časti Bratislavy a Košíc nie sú samostatné obce – sú na stránkach týchto miest.
Osobné údaje: len mená zvolených a kandidátov na starostu so stranou a hlasmi (verejné výsledky volieb).

Výstup: data/obce/<kraj>.json (obce kraja), data/obce/zoznam.json (index pre vyhľadávanie a filter), data/obce/mapa.json
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone

import statdata as sd
import zber_komunalne as zk
from spolocne import DATA, spusti, zapis_ak_zmena

VYSTUP = DATA / "obce"
OSO = ["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"]
SCITANIE = {"vek": ("om7803rr", "e_age"), "vzdelanie": ("om7809rr", "e_edu"), "narodnost": ("om7806rr", "e_national"), "nabozenstvo": ("om7805rr", "e_religion")}
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"]


def slug(t: str) -> str:
    t = unicodedata.normalize("NFD", t)
    return re.sub(r"[^a-z0-9]+", "-", "".join(c for c in t if unicodedata.category(c) != "Mn").lower()).strip("-")


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip()


def je_mc(nazov: str) -> bool:
    return bool(re.match(r"^(Bratislava|Košice)\s*-\s*\S", nazov))


# ---------------- voľby 2026 + zoznam obcí ----------------

def volby() -> tuple[dict[str, dict], dict[str, dict]]:
    """→ (obce podľa kódu: územie, výsledky)"""
    t, _ = zk.stiahni(OSO)
    if not t or not t.get("tab0d") or not t.get("tab05"):
        raise RuntimeError("Balík OSO2026 nemá výsledky")
    strany = zk.strany_mapa(t)
    uzemie: dict[str, dict] = {}
    for r in t["tab0d"]:
        kod, nazov = zk.kod(r["OBEC"]), norm(r.get("NOBEC"))
        if not kod or je_mc(nazov):
            continue
        uzemie[kod] = {"kod": kod, "nazov": nazov, "kraj": norm(r.get("NKRAJ")), "okres": norm(r.get("názov okresu") or r.get("NOKRES")),
                       "poslancov_volenych": int(zk.cislo(r.get("počet volených poslancov") or 0)) or None}
    po = lambda tab: _skup(t.get(tab, []))  # noqa: E731
    t0a, t05, t0b, t08, t02 = po("tab0a"), po("tab05"), po("tab0b"), po("tab08"), po("tab02b")
    zvol_sta = zk.zvoleni(t, "tab05", lambda r: (zk.kod(r["OBEC"]), zk.kod(r["PC_HL"])))
    zvol_pos = zk.zvoleni(t, "tab08", lambda r: (zk.kod(r["OBEC"]), zk.kod(r.get("VOOBEC", "")), zk.kod(r["PC_HL"])))
    zvs: dict[str, set] = defaultdict(set)
    for o_, pc in zvol_sta:
        zvs[o_].add(pc)
    vysl = {}
    for kod in uzemie:
        kand = t0a.get(kod, [])
        if not kand:
            continue
        zv = zvs.get(kod)
        starosta = zk.bez_klucov(zk.vysledky_kandidatov(t05.get(kod, []), kand, strany, lambda r: zk.kod(r["PC_HL"]), lambda r: True, zv or None))
        kand_p = {(zk.kod(r["VOOBEC"]), zk.kod(r["PC_HL"])): r for r in t0b.get(kod, [])}
        hl: dict[tuple, float] = defaultdict(float)
        for r in t08.get(kod, []):
            hl[(zk.kod(r["VOOBEC"]), zk.kod(r["PC_HL"]))] += zk.cislo(r["P_HL"])
        zvp = [k for k in kand_p if (kod, k[0], k[1]) in zvol_pos]
        poslanci = [{"meno": zk.meno(kand_p[k]), "strany": zk.strany_kandidata(kand_p[k], strany), "hlasy": int(hl[k]), "obvod_c": int(k[0] or 0)}
                    for k in sorted(zvp, key=lambda k: (-hl[k], k))]
        u = zk.ucast(t02.get(kod, []), {kod})
        vysl[kod] = {
            "ucast": u if u.get("zapisani") else None,
            "starosta": [{k: x[k] for k in ("meno", "strany", "hlasy", "podiel", "zvoleny")} for x in starosta[:6]],
            "kandidatov": len(starosta),
            "poslanci": poslanci, "mandaty": zk.mandaty(poslanci),
            "obvodov": len({p["obvod_c"] for p in poslanci}),
        }
    print(f"Voľby 2026: {len(uzemie)} obcí, výsledky {len(vysl)}")
    return uzemie, vysl


def _skup(riadky: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for r in riadky:
        out[zk.kod(r.get("OBEC", ""))].append(r)
    return out


# ---------------- obyvatelia a sčítanie (STATdata) ----------------

def _okres_kluc(n14: str) -> str:
    return norm(re.sub(r"^Okres\s+", "", n14))


def obyvatelia() -> dict[tuple, dict]:
    out: dict[tuple, dict] = defaultdict(dict)
    for r in sd.riadky("om7101rr"):
        n = norm(re.sub(r"^(\S.*?) I-[IV]+$", r"\1", r["e_nuts15"]))
        okres = _okres_kluc(r["e_nuts14"])
        out[(okres, n)][str(int(r["e_year"]) - 1)] = int(r["hodnota"])
    return out


def scitanie() -> dict[tuple, dict]:
    out: dict[tuple, dict] = defaultdict(dict)
    for tema, (kocka, stlpec) in SCITANIE.items():
        rows = [x for x in sd.riadky(kocka) if x.get("e_year", "2021") == "2021"]
        ostatne = [c for c in rows[0] if c not in ("e_nuts14", "e_nuts15", "e_year", "hodnota", stlpec)]
        ma_spolu = {c: any(x[c] == "Spolu" for x in rows) for c in ostatne}
        for x in rows:
            if any(ma_spolu[c] and x[c] != "Spolu" for c in ostatne):
                continue
            k = (_okres_kluc(x["e_nuts14"]), norm(x["e_nuts15"]))
            d = out[k].setdefault(tema, defaultdict(float))
            d[x[stlpec]] += x["hodnota"]
    return out


# ---------------- poloha a mapa (OSM) ----------------

def _overpass(dotaz: str) -> dict:
    import requests
    chyba = None
    for u in OVERPASS:
        try:
            r = requests.post(u, data={"data": dotaz}, timeout=600, headers={"User-Agent": "mestovcislach.sk"})
            if r.status_code == 200:
                return r.json()
            chyba = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            chyba = str(e)
    raise RuntimeError(f"Overpass: {chyba}")


def polohy() -> dict[str, tuple[float, float]]:
    """kód obce (OSM ref) → (lat, lon) stredu obce."""
    d = _overpass('[out:json][timeout:300];area["ISO3166-1"="SK"][admin_level=2]->.sk;'
                  'rel(area.sk)["boundary"="administrative"]["admin_level"~"^(9|8)$"]["ref"];out center tags;')
    out = {}
    for e in d.get("elements", []):
        ref = str(e.get("tags", {}).get("ref", "")).strip()
        c = e.get("center")
        if re.fullmatch(r"\d{6}", ref) and c:
            out[ref] = (round(c["lat"], 4), round(c["lon"], 4))
    print(f"OSM: poloha {len(out)} obcí")
    return out


def mapa() -> dict:
    """Zjednodušené hranice krajov a okresov (GeoJSON v stupňoch) pre SVG mapu."""
    from shapely.geometry import LineString, mapping
    from shapely.ops import polygonize, unary_union
    out = {}
    for uroven, kluc in ((4, "kraje"), (6, "okresy")):
        d = _overpass(f'[out:json][timeout:600];area["ISO3166-1"="SK"][admin_level=2]->.sk;'
                      f'rel(area.sk)["boundary"="administrative"]["admin_level"="{uroven}"];out geom;')
        prvky = []
        for e in d.get("elements", []):
            ciary = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in e.get("members", []) if m.get("type") == "way" and m.get("geometry") and len(m["geometry"]) > 1]
            if not ciary:
                continue
            g = unary_union(list(polygonize(unary_union(ciary))))
            if g.is_empty:
                continue
            g = g.simplify(0.004 if uroven == 6 else 0.006, preserve_topology=True)
            nazov = e["tags"].get("name", "")
            prvky.append({"nazov": nazov, "geom": json.loads(json.dumps(mapping(g)))})
        out[kluc] = prvky
        print(f"OSM: {kluc} {len(prvky)}")
    # súradnice zaokrúhliť (menší súbor)
    def zaokr(x):
        return [zaokr(y) for y in x] if isinstance(x, (list, tuple)) and x and isinstance(x[0], (list, tuple)) else [round(x[0], 3), round(x[1], 3)]
    for k in out.values():
        for p in k:
            p["geom"]["coordinates"] = zaokr(p["geom"]["coordinates"])
    return out


# ---------------- spojenie ----------------

def main() -> int:
    VYSTUP.mkdir(parents=True, exist_ok=True)
    uzemie, vysl = volby()
    obyv, scit = obyvatelia(), scitanie()
    stare_zoz = json.loads((VYSTUP / "zoznam.json").read_text(encoding="utf-8")) if (VYSTUP / "zoznam.json").exists() else {}
    stare_polohy = {o["kod"]: tuple(o["poloha"]) for o in stare_zoz.get("obce", []) if o.get("poloha")}
    try:
        pol = polohy() or stare_polohy
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Obce – poloha::{e}")
        pol = stare_polohy
    try:
        mp = mapa()
        if len(mp.get("kraje", [])) == 8 and 70 <= len(mp.get("okresy", [])) <= 90:
            zapis_ak_zmena(VYSTUP / "mapa.json", {"zdroj": "© prispievatelia OpenStreetMap (ODbL)", **mp}, kompaktne=True)
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Obce – mapa::{e}")

    po_krajoch: dict[str, list] = defaultdict(list)
    zoznam = []
    pouzite: set[str] = set()
    for kod, u in sorted(uzemie.items(), key=lambda kv: (kv[1]["kraj"], kv[1]["okres"], kv[1]["nazov"])):
        ks, os_ = slug(u["kraj"]), slug(u["okres"])
        s_ = slug(u["nazov"])
        if f"{ks}/{os_}/{s_}" in pouzite:
            s_ = f"{s_}-{kod}"
        pouzite.add(f"{ks}/{os_}/{s_}")
        rad = obyv.get((u["okres"], u["nazov"])) or {}
        sc = scit.get((u["okres"], u["nazov"])) or {}
        o = {**u, "slug": s_, "kraj_slug": ks, "okres_slug": os_, "poloha": list(pol[kod]) if kod in pol else None,
             "obyvatelia": dict(sorted(rad.items())), "scitanie": {k: {kk: round(vv) for kk, vv in sorted(v.items(), key=lambda kv: -kv[1])} for k, v in sc.items()},
             "volby2026": vysl.get(kod)}
        po_krajoch[ks].append(o)
        posl = rad[max(rad)] if rad else None
        st = next((x for x in (vysl.get(kod) or {}).get("starosta", []) if x["zvoleny"]), None)
        zoznam.append({"kod": kod, "nazov": u["nazov"], "kraj": u["kraj"], "okres": u["okres"], "url": f"/{ks}/{os_}/{s_}", "obyvatelia": posl,
                       "poloha": o["poloha"], "starosta": st["meno"] if st else None})
    bez_obyv = sum(1 for z in zoznam if not z["obyvatelia"])
    print(f"Obce: {len(zoznam)}, bez počtu obyvateľov {bez_obyv}, bez polohy {sum(1 for z in zoznam if not z['poloha'])}")
    if len(zoznam) < 2800 or bez_obyv > 100:
        raise RuntimeError(f"Podozrivý výsledok: {len(zoznam)} obcí, {bez_obyv} bez obyvateľov")
    for ks, obce in po_krajoch.items():
        zapis_ak_zmena(VYSTUP / f"{ks}.json", {"kraj": obce[0]["kraj"], "obce": obce}, kompaktne=True)
    zapis_ak_zmena(VYSTUP / "zoznam.json", {"zdroj": "ŠÚ SR (volbysr.sk, STATdata), OpenStreetMap", "obce": zoznam,
                                            "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="minutes")}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Obce")
