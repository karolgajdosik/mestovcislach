"""Obce a mapové vrstvy štátu: chránené územia (ŠOP SR) a zariadenia sociálnych služieb (MPSVR SR).

  chranene  – národné parky a ich ochranné pásma, chránené krajinné oblasti, chránené vtáčie územia
              (WFS ŠOP SR, www.sopsr.sk/geoserver). Obec sa priradí podľa polohy jej stredu
              (bod z data/obce/zoznam.json) – „obec leží v …“, nie podiel katastra.
  socialne  – Centrálny register poskytovateľov sociálnych služieb (WFS MPSVR SR, gis.geocloud.gov.sk,
              vrstva mpsvrsr:crpss). Len počty služieb podľa druhu a kapacita pobytových zariadení;
              mená poskytovateľov, kontakty ani štatutári sa neukladajú (časť poskytovateľov sú fyzické osoby).

Výstupy data/obce/chranene.json, data/obce/socialne.json.
"""

from __future__ import annotations

import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE, PODLA_NAZVU, kluc

POL = {o["kod"]: o.get("poloha") for o in OBCE if o.get("poloha")}
UA = {"User-Agent": "mestovcislach.sk (info@mestovcislach.sk)"}


def wfs(base: str, typ: str) -> list[dict]:
    r = s.get(base, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": typ,
                            "outputFormat": "application/json", "srsName": "EPSG:4326"}, headers=UA, timeout=600)
    r.raise_for_status()
    return r.json()["features"]


def zapis(nazov: str, obsah: dict) -> None:
    zapis_ak_zmena(DATA / "obce" / f"{nazov}.json", {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), **obsah}, kompaktne=True)


# ---------------- chránené územia ----------------

SOP = "https://www.sopsr.sk/geoserver"
VRSTVY = [  # (kľúč, WFS, typ, názov z vlastností, filter)
    ("np", f"{SOP}/sz/chranene_uzemia_np_s_op/ows", "sz:chranene_uzemia_np_s_op", "Nazov_uzemia", lambda p: str(p.get("category_id")) == "8"),
    ("op", f"{SOP}/sz/chranene_uzemia_np_s_op/ows", "sz:chranene_uzemia_np_s_op", "Nazov_uzemia", lambda p: str(p.get("category_id")) == "9"),
    ("chko", f"{SOP}/chranene_objekty/chranene_uzemia_vchu/ows", "chranene_objekty:chranene_uzemia_vchu", "SITETITLE_SK",
     lambda p: str(p.get("CATEGORY")) != "8"),
    ("chvu", f"{SOP}/chranene_objekty/chranene_uzemia_chvu/ows", "chranene_objekty:chranene_uzemia_chvu", "SITETITLE_SK", lambda p: True),
]


def nazov_op(n: str) -> str:
    """„OP NP Malá Fatra“, „OP4 TANAP“ -> „NP Malá Fatra“, „TANAP“."""
    return re.sub(r"^OP\d*\s+", "", n).strip()


POLE_NAZOV = ("SITETITLE_SK", "Nazov_uzemia", "NAZOV", "nazov", "NAZOV_UZEM", "name")
KATASTER = [  # (kľúč, WFS, typ) – priradenie podľa zásahu do územia obce (hranice OSM), nie podľa stredu
    ("uev", f"{SOP}/chranene_objekty/ows", "chranene_objekty:chranene_uzemia_uev"),
    ("mchu", f"{SOP}/chranene_objekty/ows", "chranene_objekty:chranene_uzemia_mchu"),
]


def _nazov(p: dict) -> str:
    for k in POLE_NAZOV:
        if p.get(k):
            return str(p[k]).strip()
    return ""


def kataster(obce: dict) -> dict:
    """Územia európskeho významu a maloplošné chránené územia, ktoré zasahujú do obce (aspoň 1 % plochy územia
    alebo 5 ha v obci), a počet chránených stromov v obci."""
    import shapely
    from shapely import STRtree
    from shapely.geometry import shape
    from zber_obce_wiki_osm import hranice
    hr = hranice()
    kody = list(hr)
    strom_obci = STRtree([hr[k] for k in kody])
    pocty = {}
    for kl, base, typ in KATASTER:
        feats = [x for x in wfs(base, typ) if x.get("geometry")]
        pocty[kl] = len(feats)
        for x in feats:
            n = _nazov(x.get("properties") or {})
            g = shape(x["geometry"])
            if not n or g.is_empty:
                continue
            if not g.is_valid:
                g = g.buffer(0)
            for i in strom_obci.query(g):
                cast = shapely.intersection(hr[kody[i]], g).area
                if cast > 0.01 * g.area or cast > 5 * 1.3e-6:  # 5 ha ≈ 6,5e-6 °² na 48,7° s. š.; dolná hranica proti šumu hraníc
                    zoz = obce[kody[i]].setdefault(kl, [])
                    if n not in zoz:
                        zoz.append(n)
    stromy = [x for x in wfs(f"{SOP}/chranene_objekty/ows", "chranene_objekty:chranene_stromy") if x.get("geometry")]
    pocty["stromy"] = len(stromy)
    for x in stromy:
        g = shape(x["geometry"])
        bod = g if g.geom_type == "Point" else g.representative_point()
        for i in strom_obci.query(bod):
            if hr[kody[i]].covers(bod):
                obce[kody[i]]["stromy"] = obce[kody[i]].get("stromy", 0) + 1
                break
    for v in obce.values():
        for kl in ("uev", "mchu"):
            if kl in v:
                v[kl] = sorted(v[kl])
    print(f"  ÚEV/MCHÚ/stromy: {pocty}; obcí s ÚEV {sum('uev' in v for v in obce.values())}, s MCHÚ {sum('mchu' in v for v in obce.values())}, "
          f"so stromami {sum('stromy' in v for v in obce.values())}")
    return pocty


def chranene() -> None:
    from shapely.geometry import Point, shape
    from shapely.prepared import prep
    obce: dict[str, dict] = defaultdict(dict)
    pocty = {}
    for kl, base, typ, pole, f in VRSTVY:
        feats = [x for x in wfs(base, typ) if x.get("geometry") and f(x.get("properties") or {})]
        pocty[kl] = len(feats)
        geo = [(str(x["properties"].get(pole) or "").strip(), prep(shape(x["geometry"]))) for x in feats]
        for kod, (lat, lon) in POL.items():
            bod = Point(lon, lat)
            nazvy = sorted({nazov_op(n) if kl == "op" else n for n, g in geo if n and g.contains(bod)})
            if nazvy:
                obce[kod][kl] = nazvy
    for v in obce.values():  # obec v národnom parku nie je zároveň „v jeho ochrannom pásme“
        if "np" in v and "op" in v:
            v["op"] = [n for n in v["op"] if n not in v["np"]] or None
            if not v["op"]:
                del v["op"]
    try:
        pocty.update(kataster(obce))
    except Exception as e:  # noqa: BLE001 – veľkoplošné územia zverejníme aj bez ÚEV/MCHÚ
        print(f"::warning title=Obce vrstvy – ÚEV/MCHÚ::{e}")
    print(f"Chránené územia: vrstvy {pocty}; obcí v NP {sum('np' in v for v in obce.values())}, v OP NP {sum('op' in v for v in obce.values())}, "
          f"v CHKO {sum('chko' in v for v in obce.values())}, v CHVÚ {sum('chvu' in v for v in obce.values())}")
    if pocty.get("chko", 0) < 10 or pocty.get("np", 0) < 5:
        raise RuntimeError(f"ŠOP: podozrivo málo území {pocty}")
    zapis("chranene", {"zdroj": {"nazov": "ŠOP SR – chránené územia (WFS): národné parky s ochrannými pásmami, veľkoplošné chránené územia, chránené vtáčie územia, územia európskeho významu, maloplošné chránené územia, chránené stromy",
                                 "url": "https://www.sopsr.sk"}, "pravidlo": "NP, OP, CHKO, CHVÚ podľa polohy stredu obce; ÚEV a MCHÚ podľa zásahu do územia obce (hranice OSM)",
                       "obce": dict(sorted(obce.items()))})


# ---------------- sociálne služby ----------------

SKUPINY = {  # druh služby -> skupina na webe
    "zariadenie pre seniorov": "seniori", "zariadenie opatrovateľskej služby": "seniori", "domov sociálnych služieb": "dss",
    "špecializované zariadenie": "dss", "denný stacionár": "stacionar", "opatrovateľská služba": "opatrovatelska",
    "denné centrum": "centrum", "komunitné centrum": "komunitne", "jedáleň": "jedalen", "prepravná služba": "preprava",
    "zariadenie starostlivosti o deti do troch rokov veku dieťaťa": "jasle",
}


def obec_bodu(adresa: str, lat: float | None, lon: float | None) -> str | None:
    """Obec podľa adresy miesta poskytovania (názov obce v adrese; pri zhode názvov najbližšia), inak podľa polohy."""
    casti = [c.strip() for c in re.split(r",", adresa or "") if c.strip()]
    for c in reversed(casti):
        c2 = re.sub(r"^\d{3}\s?\d{2}\s*", "", c)  # PSČ
        c2 = re.sub(r"\s*-\s*.*$", "", c2) if c2 not in PODLA_NAZVU else c2
        kand = PODLA_NAZVU.get(kluc(c2), [])
        kand = [k for k in kand if k in POL]
        if kand:
            if len(kand) == 1 or lat is None:
                return kand[0]
            return min(kand, key=lambda k: math.dist(POL[k], (lat, lon)))
    if lat is not None:
        d, k = min((math.dist(p, (lat, lon)), k) for k, p in POL.items())
        return k if d < 0.02 else None
    return None


def socialne() -> None:
    feats = wfs("https://gis.geocloud.gov.sk/geoserver/mpsvrsr/ows", "mpsvrsr:crpss")
    obce: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    nepr = vymaz = 0
    posledny = ""
    for x in feats:
        p = x.get("properties") or {}
        if p.get("datum_vymazu"):
            vymaz += 1
            continue
        posledny = max(posledny, str(p.get("datum_zapis") or "")[:10])
        lat = lon = None
        g = x.get("geometry")
        if g and g.get("type") == "Point":
            lon, lat = g["coordinates"][:2]
        kod = obec_bodu(str(p.get("adresa_poskytovania") or ""), lat, lon)
        if not kod:
            nepr += 1
            continue
        sk = SKUPINY.get(str(p.get("druh_ss") or "").strip(), "ine")
        o = obce[kod][sk]
        o[0] += 1
        if str(p.get("forma") or "").startswith("pobytov"):
            try:
                o[1] += int(float(p.get("kapacita") or 0))
            except ValueError:
                pass
    print(f"Sociálne služby: {len(feats)} záznamov, vymazaných {vymaz}, nepriradených {nepr}, obcí {len(obce)}, posledný zápis {posledny}")
    if len(obce) < 800:
        raise RuntimeError(f"CRPSS: len {len(obce)} obcí")
    zapis("socialne", {"stav": posledny, "zdroj": {"nazov": "MPSVR SR – Centrálny register poskytovateľov sociálnych služieb (WFS)", "url": "https://gis.geocloud.gov.sk"},
                       "obce": {k: {sk: v for sk, v in d.items()} for k, d in sorted(obce.items())}})


# socialne: vrstva CRPSS vo WFS je zastaraná (posledný zápis 1. 1. 2022, ~30 % záznamov bez obce) – nezverejňujeme.
MODULY = {"chranene": chranene}


def main() -> int:
    vyber = sys.argv[1:] or list(MODULY)
    chyby = 0
    for m in vyber:
        try:
            MODULY[m]()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=Obce vrstvy – {m}::{e}")
    if chyby == len(vyber):
        raise RuntimeError("žiadny modul neprebehol")
    return 0


if __name__ == "__main__":
    spusti(main, "Obce – chránené územia a sociálne služby")
