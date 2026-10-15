"""Spádové obvody (rajonizácia) základných a materských škôl v Bratislave podľa registra adries.

Výstup: public/data/rajonizacia-bratislava.json (načíta sa v prehliadači pri vyhľadávaní adresy)
        data/rajonizacia-bratislava.json (súhrn pre stránku a asistenta)

Zdroj: data.bratislava.sk – „Rajonizácia základných škôl / predprimárneho vzdelávania podľa
registra adries“ (školský rok 2025/2026), licencia CC BY 4.0. Tabuľky bez geometrie:
každý adresný bod (ulica, súpisné a orientačné číslo) má priradenú spádovú školu.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spolocne import adresy_mv, hranice, norm_ulica, zapis_ak_zmena  # noqa: E402

KOREN = Path(__file__).resolve().parent.parent
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
ZS = "ef5254fb17344932b787dbbf81c094a5"
MS = "a6a832ddc3c94aa3b8c15b41e5a0365b"  # rajonizácia MŠ 2026 (2025: 9d734ed003a142a3b4034979e2498a7c)

s = requests.Session()
s.headers["User-Agent"] = UA


def sluzba(item: str) -> tuple[str, dict]:
    it = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{item}", params={"f": "json"}, timeout=60).json()
    url = it["url"].rstrip("/")
    url = url if url[-1].isdigit() else url + "/0"
    return url, {"nazov": it.get("title"), "url": f"https://data.bratislava.sk/datasets/{item}", "licencia": "CC BY 4.0"}


def vsetko(url: str) -> list[dict]:
    meta = s.get(url, params={"f": "json"}, timeout=60).json()
    krok = min(int(meta.get("maxRecordCount") or 1000), 2000)
    riadky, offset = [], 0
    while True:
        r = s.get(url + "/query", params={"where": "1=1", "outFields": "*", "returnGeometry": "false", "orderByFields": "ObjectId",
                                          "resultOffset": offset, "resultRecordCount": krok, "f": "json"}, timeout=120).json()
        if "error" in r:
            raise RuntimeError(f"{url}: {r['error']}")
        davka = [f["attributes"] for f in r.get("features", [])]
        riadky += davka
        if len(davka) < krok and not r.get("exceededTransferLimit"):
            return riadky
        offset += len(davka)


t = lambda x: (x or "").strip()  # noqa: E731


def g(r: dict, *mena: str) -> str:
    """Hodnota prvého existujúceho poľa – súbory 2025 a 2026 majú rôzne názvy stĺpcov."""
    for m in mena:
        if m in r and r[m] not in (None, ""):
            return str(r[m]).strip()
    return ""


def main() -> int:
    url_zs, zdroj_zs = sluzba(ZS)
    url_ms, zdroj_ms = sluzba(MS)
    zs, ms = vsetko(url_zs), vsetko(url_ms)
    print(f"ZŠ: {len(zs)} adries, MŠ: {len(ms)} adries; ukážka ZŠ: {zs[0] if zs else None}")
    if len(zs) < 10000 or len(ms) < 10000:
        raise RuntimeError(f"Podozrivo málo adries (ZŠ {len(zs)}, MŠ {len(ms)})")

    skoly: list[dict] = []
    idx_skoly: dict[tuple, int] = {}
    skolky: list[dict] = []
    idx_skolky: dict[tuple, int] = {}
    # adresa → [zš, mš]
    adresy: dict[tuple, list] = {}

    def kluc(r: dict) -> tuple:
        # „Bratislava-Petržalka“ (ZŠ) a „Petržalka“ (MŠ) je tá istá mestská časť
        mc = re.sub(r"^Bratislava\s*-\s*", "", g(r, "Mestská_časť", "mestska_cast"))
        return (mc, g(r, "Ulica", "ulica") or g(r, "Lokalita", "lokalita_zaujmu"), g(r, "Súpisné_číslo", "supisne"), g(r, "Orientačné_číslo", "orientacne"))

    for r in zs:
        sk = (t(r.get("Názov_školského_zariadenia")), t(r.get("Adresa_základnej_školy")))
        if not sk[0]:
            continue
        if sk not in idx_skoly:
            idx_skoly[sk] = len(skoly)
            skoly.append({"nazov": sk[0], "adresa": "" if "bez udania" in sk[1] else sk[1], "web": t(r.get("Web_školy")), "typ": t(r.get("Typ_školského_zariadenia"))})
        adresy.setdefault(kluc(r), [None, None])[0] = idx_skoly[sk]
    for r in ms:
        sk = (g(r, "Rajón_materskej_škôlky", "rajon"), g(r, "Adresa_materskej_škôlky", "adresa_skolky"))
        if not sk[0] and not sk[1]:
            continue
        if sk not in idx_skolky:
            idx_skolky[sk] = len(skolky)
            skolky.append({"nazov": sk[0], "adresa": sk[1]})
        adresy.setdefault(kluc(r), [None, None])[1] = idx_skolky[sk]

    # kompaktne: {"MČ": {"Ulica": [[súpisné, orientačné, zš, mš], ...]}}
    ulice: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for (mc, ulica, sup, ori), (z, m) in sorted(adresy.items()):
        if not ulica:  # adresy bez ulice aj lokality sa podľa ulice nájsť nedajú
            continue
        ulice[mc][ulica].append([sup, ori, z, m])
    verejne = {"zdroj": [zdroj_zs, zdroj_ms], "skolsky_rok": "2025/2026", "rok_zs": 2025, "rok_ms": 2026, "zs": skoly, "ms": skolky, "ulice": ulice,
               "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (KOREN / "public" / "data").mkdir(parents=True, exist_ok=True)
    cesta = KOREN / "public" / "data" / "rajonizacia-bratislava.json"
    stare = json.loads(cesta.read_text(encoding="utf-8")) if cesta.exists() else {}
    if {k: v for k, v in stare.items() if k != "aktualizovane"} != json.loads(json.dumps({k: v for k, v in verejne.items() if k != "aktualizovane"})):
        cesta.write_text(json.dumps(verejne, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        suhrn = {"zdroj": [zdroj_zs, zdroj_ms], "skolsky_rok": "2025/2026", "adries": sum(len(a) for u in ulice.values() for a in u.values()), "zakladne_skoly": len(skoly), "skolky_rajony": len(skolky),
                 "ulic": sum(len(u) for u in ulice.values()), "aktualizovane": verejne["aktualizovane"]}
        (KOREN / "data" / "rajonizacia-bratislava.json").write_text(json.dumps(suhrn, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Uložené: {suhrn}; veľkosť {cesta.stat().st_size // 1024} kB")
    else:
        print("Bez zmeny.")
    try:
        obvody(adresy, skoly)
    except Exception as e:  # noqa: BLE001 – mapa obvodov je doplnok, vyhľadávanie funguje aj bez nej
        print(f"::warning title=Obvody ZŠ na mape::{type(e).__name__}: {e}")
    return 0


def obvody(adresy: dict, skoly: list[dict]) -> None:
    """Približné územia spádových ZŠ: adresné body (register adries MV SR) → Voronoiove bunky v rámci MČ → zlúčené podľa školy."""
    from shapely.geometry import MultiPoint, Point, mapping
    from shapely.ops import unary_union, voronoi_diagram
    from shapely.strtree import STRtree

    body_mv: dict[tuple, tuple] = {}
    for a in adresy_mv():
        body_mv.setdefault((a["mc"], norm_ulica(a["ulica"]), a["sup"], a["ori"].lower()), (a["lon"], a["lat"]))
        body_mv.setdefault((a["mc"], norm_ulica(a["ulica"]), "", a["ori"].lower()), (a["lon"], a["lat"]))
        body_mv.setdefault((a["mc"], norm_ulica(a["ulica"]), a["sup"], ""), (a["lon"], a["lat"]))
    po_mc: dict[str, dict[tuple, int]] = defaultdict(dict)
    najdene = 0
    for (mc, ulica, sup, ori), (z, _m) in adresy.items():
        if z is None:
            continue
        u = norm_ulica(ulica)
        bod = body_mv.get((mc, u, sup, ori.lower())) or body_mv.get((mc, u, "", ori.lower())) or body_mv.get((mc, u, sup, ""))
        if bod:
            po_mc[mc][(round(bod[0], 6), round(bod[1], 6))] = z
            najdene += 1
    print(f"Obvody: {najdene} z {sum(1 for v in adresy.values() if v[0] is not None)} adries so ZŠ má súradnice")
    features = []
    for _, nazov_mc, hranica in hranice():
        body = po_mc.get(nazov_mc, {})
        skupiny: dict[int, list] = defaultdict(list)
        if len({*body.values()}) <= 1:
            if body:
                skupiny[next(iter(body.values()))].append(hranica)
        else:
            vor = voronoi_diagram(MultiPoint([list(b) for b in body]), envelope=hranica.envelope.buffer(0.01))
            klud = list(body)
            strom = STRtree([Point(b) for b in klud])
            for bunka in vor.geoms:
                orez = bunka.intersection(hranica)
                if orez.is_empty:
                    continue
                idx = strom.query(bunka, predicate="contains")
                if len(idx):
                    skupiny[body[klud[int(idx[0])]]].append(orez)
        for z, casti in skupiny.items():
            g = unary_union(casti).simplify(0.00008, preserve_topology=True)
            sk = skoly[z]
            gj = json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), 5))
            features.append({"type": "Feature", "properties": {"zs": z, "nazov": sk["nazov"], "adresa": sk["adresa"], "web": sk["web"], "mc": nazov_mc}, "geometry": gj})
    if len(features) < 30:
        raise RuntimeError(f"Málo obvodov ({len(features)})")
    vystup = {"type": "FeatureCollection", "features": features, "zdroj": "Rajonizácia ZŠ (data.bratislava.sk) + register adries MV SR; hranice sú približné (podľa najbližších adries)"}
    cesta = KOREN / "public" / "data" / "obvody-zs-bratislava.geojson"
    if zapis_ak_zmena(cesta, vystup, kompaktne=True):
        print(f"Obvody uložené: {len(features)} území, {cesta.stat().st_size // 1024} kB")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber rajonizácie::{type(e).__name__}: {sprava}")
        sys.exit(1)
