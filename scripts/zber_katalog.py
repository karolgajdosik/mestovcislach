"""Inventár všetkých datasetov portálu data.bratislava.sk (ArcGIS Hub).

Pre každý dataset zistí typ, odkaz na službu, vrstvy a tabuľky (polia, geometria, počet záznamov),
jazyk, dátum zmeny a licenciu. Slúži na triedenie (čo web používa, čo sa dá importovať a prečo
sa niečo vynecháva) a pre všeobecný import tabuliek (zber_tabulky.py).

Výstup: data/katalog-bratislava.json
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena

HUB = "https://data.bratislava.sk/api/search/v1/collections/dataset/items"
ITEM = "https://www.arcgis.com/sharing/rest/content/items/{}"


def prechod(params: dict) -> list[dict]:
    polozky, url, params = [], HUB, {"limit": 100, **params}
    while url:
        r = s.get(url, params=params, timeout=120)
        r.raise_for_status()
        j = r.json()
        for f in j.get("features", []):
            p = f.get("properties", {})
            polozky.append({"id": p.get("id") or f.get("id"), "nazov": p.get("title"), "typ": p.get("type"), "url": p.get("url"),
                            "tagy": p.get("tags") or [], "kategorie": p.get("categories") or [], "upravene": p.get("modified"),
                            "popis": re.sub(r"<[^>]+>", " ", p.get("snippet") or p.get("description") or "")[:400].strip()})
        url = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
        params = None
    return polozky


def zoznam() -> list[dict]:
    """Stránkovanie Hubu nie je stabilné (položky sa medzi stránkami presúvajú) – zlúčime viac prechodov s rôznym triedením."""
    vsetky: dict[str, dict] = {}
    for params in ({}, {"sortby": "properties.title"}, {"sortby": "-properties.title"}, {"sortby": "properties.modified"}, {"sortby": "-properties.modified"}):
        try:
            p = prechod(params)
        except Exception as e:  # noqa: BLE001
            print(f"Prechod {params}: {e}")
            continue
        nove = sum(1 for x in p if x["id"] not in vsetky)
        for x in p:
            vsetky.setdefault(x["id"], x)
        print(f"Prechod {params or 'predvolený'}: {len(p)} položiek, {len({x['id'] for x in p})} unikátnych, nových {nove}; spolu {len(vsetky)}")
    return list(vsetky.values())


def detail(p: dict) -> dict:
    try:
        it = s.get(ITEM.format(p["id"]), params={"f": "json"}, timeout=60).json()
    except Exception as e:  # noqa: BLE001
        p["chyba"] = f"item: {e}"
        return p
    p["typ"] = it.get("type") or p["typ"]
    p["url"] = it.get("url") or p["url"]
    p["jazyk"] = it.get("culture")
    p["licencia"] = re.sub(r"<[^>]+>", " ", it.get("licenseInfo") or "")[:120].strip()
    p["velkost"] = it.get("size")
    p["typove_slova"] = it.get("typeKeywords", [])[:12]
    p["upravene_ms"] = it.get("modified")
    if not p.get("popis"):
        p["popis"] = re.sub(r"<[^>]+>", " ", it.get("snippet") or it.get("description") or "")[:400].strip()
    url = (p.get("url") or "").rstrip("/")
    if "FeatureServer" in url or "MapServer" in url:
        zaklad = re.sub(r"/\d+$", "", url)
        try:
            sl = s.get(zaklad, params={"f": "json"}, timeout=60).json()
            casti = [(x["id"], x.get("name"), "vrstva") for x in sl.get("layers", [])] + [(x["id"], x.get("name"), "tabulka") for x in sl.get("tables", [])]
            if re.search(r"/\d+$", url):
                cislo = int(url.rsplit("/", 1)[1])
                casti = [c for c in casti if c[0] == cislo] or casti
            vrstvy = []
            for cid, meno, druh in casti[:8]:
                m = s.get(f"{zaklad}/{cid}", params={"f": "json"}, timeout=60).json()
                pocet = s.get(f"{zaklad}/{cid}/query", params={"where": "1=1", "returnCountOnly": "true", "f": "json"}, timeout=60).json().get("count")
                vrstvy.append({"id": cid, "nazov": meno, "druh": druh, "geometria": m.get("geometryType"), "pocet": pocet,
                               "polia": [[f["name"], f.get("type", "").replace("esriFieldType", ""), f.get("alias")] for f in m.get("fields", [])][:60]})
            p["sluzba"] = zaklad
            p["vrstvy"] = vrstvy
        except Exception as e:  # noqa: BLE001
            p["chyba"] = f"služba: {e}"
    return p


def main() -> int:
    polozky = zoznam()
    if len(polozky) < 300:
        raise RuntimeError(f"Katalóg: len {len(polozky)} položiek")
    with ThreadPoolExecutor(8) as ex:
        polozky = list(ex.map(detail, polozky))
    polozky.sort(key=lambda p: (p.get("nazov") or "").lower())
    zapis_ak_zmena(DATA / "katalog-bratislava.json", {"zdroj": "https://data.bratislava.sk", "pocet": len(polozky), "datasety": polozky,
                                                      "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    typy: dict[str, int] = {}
    for p in polozky:
        typy[p.get("typ") or "?"] = typy.get(p.get("typ") or "?", 0) + 1
    print(f"Datasetov {len(polozky)}; typy {typy}; s chybou {sum(1 for p in polozky if p.get('chyba'))}")
    return 0


if __name__ == "__main__":
    spusti(main, "Inventár katalógu")
