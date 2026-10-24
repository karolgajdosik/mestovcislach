"""Strategické hlukové mapy aglomerácie Bratislava – Úrad verejného zdravotníctva SR.

Zdroj: data.slovensko.sk – „Hluková vrstevnicová mapa pre hluk z ciest / z priemyslu
v aglomeráciách“ (INSPIRE, WFS gis.geocloud.gov.sk/geoserver/uvz). Izofóny (čiary rovnakej
hladiny hluku) 55, 60, 65 a 70 dB pre Lden (celodenný ukazovateľ) a Lnight (noc).
WMS služba ich kreslí jednou farbou, preto čiary sťahujeme a farbíme podľa hladiny sami.

Výstup: public/data/hluk-bratislava.json (načíta sa až po zapnutí vrstvy na mape)
"""

from __future__ import annotations

from datetime import datetime, timezone

from shapely.geometry import LineString, MultiLineString, shape
from shapely.ops import unary_union

from spolocne import DATA, VEREJNE, hranice, s, spusti, zapis_ak_zmena  # noqa: F401

WFS = "https://gis.geocloud.gov.sk/geoserver/uvz/ows"
VRSTVY = {
    "cesty_lden": ("Hluk z ciest – celý deň (Lden)", "pd_8_07_hlukova_vrstevnicova_mapa_pre_hluk_z_ciest_v_aglomeraciach_lden"),
    "cesty_lnight": ("Hluk z ciest – noc (Lnight)", "pd_8_08_hlukova_vrstevnicova_mapa_pre_hluk_z_ciest_v_aglomeraciach_lnight"),
    "priemysel_lden": ("Hluk z priemyslu – celý deň (Lden)", "pd_8_13_hlukova_vrstevnicova_mapa_pre_hluk_z_priemyslu_v_aglomeraciach_lden"),
}
ZDROJ = {"nazov": "Úrad verejného zdravotníctva SR – strategické hlukové mapy aglomerácie Bratislava", "url": "https://data.slovensko.sk/datasety", "licencia": "otvorené dáta (data.slovensko.sk, INSPIRE)"}


def ciary(g) -> list:
    if g.is_empty:
        return []
    if isinstance(g, LineString):
        return [g]
    if isinstance(g, MultiLineString):
        return list(g.geoms)
    return [x for sub in getattr(g, "geoms", []) for x in ciary(sub)]


def main() -> int:
    mesto = unary_union([g for _, _, g in hranice()]).buffer(0.002)
    vystup = {"zdroj": ZDROJ, "urovne": [55, 60, 65, 70], "vrstvy": {}}
    for kluc, (nazov, vrstva) in VRSTVY.items():
        r = s.get(WFS, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "uvz:" + vrstva,
                               "outputFormat": "application/json", "bbox": "48.0,16.9,48.3,17.4,urn:ogc:def:crs:EPSG::4326", "count": 50000}, timeout=600)
        r.raise_for_status()
        po_urovni: dict[str, list] = {}
        bodov = 0
        for f in r.json().get("features", []):
            uroven = str(f["properties"].get("name") or "").strip()
            if uroven not in ("55", "60", "65", "70") or not f.get("geometry"):
                continue
            g = shape(f["geometry"]).intersection(mesto).simplify(0.00004)
            for c in ciary(g):
                if c.length < 0.0003:
                    continue
                suradnice = [[round(y, 5), round(x, 5)] for x, y in c.coords]
                bodov += len(suradnice)
                po_urovni.setdefault(uroven, []).append(suradnice)
        if not po_urovni:
            raise RuntimeError(f"{vrstva}: žiadne izofóny v Bratislave")
        vystup["vrstvy"][kluc] = {"nazov": nazov, "ciary": po_urovni}
        print(f"{kluc}: {sum(len(v) for v in po_urovni.values())} čiar, {bodov} bodov")
    vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if zapis_ak_zmena(VEREJNE / "hluk-bratislava.json", vystup, kompaktne=True):
        print(f"Uložené: {(VEREJNE / 'hluk-bratislava.json').stat().st_size // 1024} kB")
    return 0


if __name__ == "__main__":
    spusti(main, "Zber hlukových máp")
