"""Chránená príroda v Bratislave: národné chránené územia a Natura 2000 (EEA).

Výstupy:
  data/priroda-bratislava.json            – rozlohy v meste a podľa mestských častí, zoznam území
  public/data/priroda-bratislava.geojson  – polygóny orezané na hranicu mesta (pre mapu)

Zdroj: Európska environmentálna agentúra (EEA), ArcGIS služby bio.discomap.eea.europa.eu:
  - Nationally designated areas (NatDA, predtým CDDA) – údaje dodáva SR (ŠOP SR / MŽP SR)
  - Natura 2000 (vydanie 2024)
Kategórie IUCN prekladáme orientačne na slovenské kategórie ochrany.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

KOREN = Path(__file__).resolve().parent.parent
DATA = KOREN / "data"
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
EEA = "https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/"
OBALKA = {"geometry": "16.95,48.0,17.4,48.3", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
          "spatialRel": "esriSpatialRelIntersects", "outSR": 4326, "f": "geojson", "outFields": "*"}
KATEGORIE = {
    "V": "Chránená krajinná oblasť",
    "Ia": "Prírodná rezervácia (prísna ochrana)",
    "Ib": "Prírodná rezervácia",
    "II": "Národný park",
    "III": "Prírodná pamiatka",
    "IV": "Chránený areál / rezervácia",
    "notApplicable": "Ochranné pásmo",
}


def stiahni(sluzba: str, vrstva: int, where: str) -> list[dict]:
    r = requests.get(f"{EEA}{sluzba}/MapServer/{vrstva}/query", params={**OBALKA, "where": where},
                     headers={"User-Agent": UA}, timeout=180)
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(f"EEA {sluzba}/{vrstva}: {d['error']}")
    return d.get("features", [])


def main() -> int:
    hranice = json.loads((DATA / "hranice-bratislava.geojson").read_text(encoding="utf-8"))
    obyv = json.loads((DATA / "obyvatelstvo-bratislava.json").read_text(encoding="utf-8"))
    nazvy = {c["kod"][-6:]: c["nazov_kratky"] for c in obyv["mestske_casti"]}
    do_utm = Transformer.from_crs(4326, 32633, always_xy=True).transform
    casti = [(f["properties"]["kod_obce"], shape(f["geometry"])) for f in hranice["features"]]
    mesto = unary_union([g for _, g in casti])
    mesto_km2 = transform(do_utm, mesto).area / 1e6

    def km2(g) -> float:
        return transform(do_utm, g).area / 1e6

    vrstvy = {
        "narodne": [f for f in stiahni("CDDA_Dyna_WM", 4, "countryCode='SK'") if f.get("geometry")],
        "natura": [f for f in stiahni("Natura2000Sites", 2, "MS='SK'") if f.get("geometry")],
    }
    if len(vrstvy["narodne"]) < 10:
        raise RuntimeError(f"EEA: podozrivo málo národných území ({len(vrstvy['narodne'])}).")

    prvky, uzemia = [], []
    zjednotenie = {"narodne": [], "natura": []}
    po_kategoriach: dict[str, float] = defaultdict(float)
    for typ, features in vrstvy.items():
        for f in features:
            g = shape(f["geometry"]).buffer(0)
            v_meste = g.intersection(mesto)
            if v_meste.is_empty or km2(v_meste) < 0.0005:
                continue
            p = f["properties"]
            if typ == "narodne":
                kat = p.get("iucnCategory") or "notApplicable"
                nazov, popis = p.get("siteName"), KATEGORIE.get(kat, kat)
                if kat != "notApplicable":
                    zjednotenie["narodne"].append(v_meste)
                    po_kategoriach[popis] += km2(v_meste)
            else:
                kat = {"A": "SPA", "B": "SCI", "C": "SPA+SCI"}.get(p.get("SITETYPE"), p.get("SITETYPE"))
                nazov = p.get("SITENAME")
                popis = "Chránené vtáčie územie" if kat == "SPA" else "Územie európskeho významu" if kat == "SCI" else "Natura 2000"
                zjednotenie["natura"].append(v_meste)
            plocha = round(km2(v_meste), 2)
            uzemia.append({"typ": typ, "nazov": nazov, "kategoria": popis, "km2_v_meste": plocha,
                           "kod": p.get("SITECODE") or p.get("natDAId")})
            zj = v_meste.simplify(0.0001, preserve_topology=True)
            geo = mapping(zj)
            prvky.append({"type": "Feature", "properties": {"t": typ, "n": nazov, "k": popis, "km2": plocha},
                          "geometry": json.loads(json.dumps(geo, default=list), parse_float=lambda x: round(float(x), 5))})

    narodne = unary_union(zjednotenie["narodne"]) if zjednotenie["narodne"] else None
    natura = unary_union(zjednotenie["natura"]) if zjednotenie["natura"] else None
    po_castiach = []
    for kod, g in casti:
        plocha = km2(g)
        n1 = km2(g.intersection(narodne)) if narodne else 0
        n2 = km2(g.intersection(natura)) if natura else 0
        po_castiach.append({"kod_obce": kod, "nazov": nazvy.get(kod, kod), "km2": round(plocha, 2),
                            "chranene_km2": round(n1, 2), "chranene_pct": round(100 * n1 / plocha, 1),
                            "natura_km2": round(n2, 2), "natura_pct": round(100 * n2 / plocha, 1)})
    po_castiach.sort(key=lambda c: -c["chranene_pct"])

    (KOREN / "public" / "data").mkdir(parents=True, exist_ok=True)
    (KOREN / "public" / "data" / "priroda-bratislava.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": prvky}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    vystup = {
        "zdroj": {"nazov": "Európska environmentálna agentúra (EEA) – NatDA a Natura 2000",
                  "url": "https://www.eea.europa.eu/en/datahub", "licencia": "EEA – voľné použitie s uvedením zdroja"},
        "mesto": {
            "km2": round(mesto_km2, 1),
            "chranene_km2": round(km2(narodne), 1) if narodne else 0,
            "chranene_pct": round(100 * km2(narodne) / mesto_km2, 1) if narodne else 0,
            "natura_km2": round(km2(natura), 1) if natura else 0,
            "natura_pct": round(100 * km2(natura) / mesto_km2, 1) if natura else 0,
            "kategorie": {k: round(v, 1) for k, v in sorted(po_kategoriach.items(), key=lambda x: -x[1])},
        },
        "mestske_casti": po_castiach,
        "uzemia": sorted(uzemia, key=lambda u: (u["typ"], -u["km2_v_meste"])),
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (DATA / "priroda-bratislava.json").write_text(json.dumps(vystup, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK príroda: {vystup['mesto']}, {len(uzemia)} území")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber prírody::{type(e).__name__}: {sprava}")
        sys.exit(1)
