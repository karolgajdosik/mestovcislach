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
    print(f"Chránené územia: vrstvy {pocty}; obcí v NP {sum('np' in v for v in obce.values())}, v OP NP {sum('op' in v for v in obce.values())}, "
          f"v CHKO {sum('chko' in v for v in obce.values())}, v CHVÚ {sum('chvu' in v for v in obce.values())}")
    if pocty.get("chko", 0) < 10 or pocty.get("np", 0) < 5:
        raise RuntimeError(f"ŠOP: podozrivo málo území {pocty}")
    zapis("chranene", {"zdroj": {"nazov": "ŠOP SR – chránené územia (WFS): národné parky s ochrannými pásmami, veľkoplošné chránené územia, chránené vtáčie územia",
                                 "url": "https://www.sopsr.sk"}, "pravidlo": "podľa polohy stredu obce",
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


MODULY = {"chranene": chranene, "socialne": socialne}


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
