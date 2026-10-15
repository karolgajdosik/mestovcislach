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
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

KOREN = Path(__file__).resolve().parent.parent
UA = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"
ZS = "ef5254fb17344932b787dbbf81c094a5"
MS = "9d734ed003a142a3b4034979e2498a7c"

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
        return (t(r.get("Mestská_časť")), t(r.get("Ulica")) or t(r.get("Lokalita")), t(r.get("Súpisné_číslo")), t(r.get("Orientačné_číslo")))

    for r in zs:
        sk = (t(r.get("Názov_školského_zariadenia")), t(r.get("Adresa_základnej_školy")))
        if not sk[0]:
            continue
        if sk not in idx_skoly:
            idx_skoly[sk] = len(skoly)
            skoly.append({"nazov": sk[0], "adresa": sk[1], "web": t(r.get("Web_školy")), "typ": t(r.get("Typ_školského_zariadenia"))})
        adresy.setdefault(kluc(r), [None, None])[0] = idx_skoly[sk]
    for r in ms:
        sk = (t(r.get("Rajón_materskej_škôlky")), t(r.get("Adresa_materskej_škôlky")))
        if not sk[0] and not sk[1]:
            continue
        if sk not in idx_skolky:
            idx_skolky[sk] = len(skolky)
            skolky.append({"nazov": sk[0], "adresa": sk[1]})
        adresy.setdefault(kluc(r), [None, None])[1] = idx_skolky[sk]

    # kompaktne: {"MČ": {"Ulica": [[súpisné, orientačné, zš, mš], ...]}}
    ulice: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for (mc, ulica, sup, ori), (z, m) in sorted(adresy.items()):
        ulice[mc][ulica].append([sup, ori, z, m])
    verejne = {"zdroj": [zdroj_zs, zdroj_ms], "skolsky_rok": "2025/2026", "zs": skoly, "ms": skolky, "ulice": ulice,
               "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (KOREN / "public" / "data").mkdir(parents=True, exist_ok=True)
    cesta = KOREN / "public" / "data" / "rajonizacia-bratislava.json"
    stare = json.loads(cesta.read_text(encoding="utf-8")) if cesta.exists() else {}
    if {k: v for k, v in stare.items() if k != "aktualizovane"} != json.loads(json.dumps({k: v for k, v in verejne.items() if k != "aktualizovane"})):
        cesta.write_text(json.dumps(verejne, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        suhrn = {"zdroj": [zdroj_zs, zdroj_ms], "skolsky_rok": "2025/2026", "adries": len(adresy), "zakladne_skoly": len(skoly), "skolky_rajony": len(skolky),
                 "ulic": sum(len(u) for u in ulice.values()), "aktualizovane": verejne["aktualizovane"]}
        (KOREN / "data" / "rajonizacia-bratislava.json").write_text(json.dumps(suhrn, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Uložené: {suhrn}; veľkosť {cesta.stat().st_size // 1024} kB")
    else:
        print("Bez zmeny.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"CHYBA: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            sprava = str(e).replace("%", "%25").replace("\r", "").replace("\n", "%0A")
            print(f"::error title=Zber rajonizácie::{type(e).__name__}: {sprava}")
        sys.exit(1)
