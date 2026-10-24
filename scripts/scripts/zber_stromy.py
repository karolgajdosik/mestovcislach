"""Chránené stromy v Bratislave – Štátna ochrana prírody SR (štátny zoznam).

Zdroj: data.slovensko.sk – „Chránené stromy“ (ŠOP SR), WFS
www.sopsr.sk/geoserver/chranene_objekty/chranene_stromy (S-JTSK, EPSG:5514).
Nahrádza neúplný zoznam chránených stromov z OpenStreetMap.

Výstup: public/data/stromy-sop.json
"""

from __future__ import annotations

from datetime import datetime, timezone

from pyproj import Transformer

from spolocne import VEREJNE, mc_podla_polohy, s, spusti, zapis_ak_zmena

WFS = "https://www.sopsr.sk/geoserver/chranene_objekty/chranene_stromy/ows"
ZDROJ = {"nazov": "ŠOP SR – štátny zoznam chránených stromov", "url": "https://www.sopsr.sk", "licencia": "otvorené dáta (data.slovensko.sk)"}


def main() -> int:
    r = s.get(WFS, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "chranene_objekty:chranene_stromy",
                           "outputFormat": "application/json", "count": 10000}, timeout=300)
    r.raise_for_status()
    features = r.json().get("features", [])
    if len(features) < 500:
        raise RuntimeError(f"Málo chránených stromov ({len(features)})")
    tr = Transformer.from_crs("EPSG:5514", "EPSG:4326", always_xy=True)
    najdi_mc = mc_podla_polohy()
    body = []
    for f in features:
        g = f.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        lon, lat = tr.transform(*g["coordinates"][:2])
        mc = najdi_mc(lon, lat)
        if not mc:
            continue
        p = f["properties"]
        det = {k: v for k, v in {"druh": p.get("Druh"), "pocet": p.get("Pocet_stromov"), "lok": p.get("Lokalita"), "dovod": p.get("Dovod_ochrany"),
                                  "url": p.get("Odkaz_na_statny_zoznam"), "c": p.get("Cislo_statneho_zoznamu"), "mc": mc}.items() if v not in (None, "")}
        body.append([round(lat, 6), round(lon, 6), (p.get("Nazov_chraneneho_stromu") or "Chránený strom").strip(), det])
    if len(body) < 10:
        raise RuntimeError(f"Málo chránených stromov v Bratislave ({len(body)})")
    body.sort(key=lambda b: (b[3].get("c") or 0, b[2]))
    zapis_ak_zmena(VEREJNE / "stromy-sop.json", {"zdroj": ZDROJ, "body": body, "chranenych_objektov": len({b[3].get('c') for b in body}),
                                                 "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")}, kompaktne=True)
    print(f"Chránené stromy v BA: {len(body)} stromov, {len({b[3].get('c') for b in body})} chránených objektov")
    return 0


if __name__ == "__main__":
    spusti(main, "Zber chránených stromov")
