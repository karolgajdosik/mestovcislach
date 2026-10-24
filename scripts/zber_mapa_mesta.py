"""Mapa mesta z bodových a čiarových vrstiev jeho portálu otvorených dát (ArcGIS Hub).

Vstup: data/katalog-<mesto>.json (zber_katalog.py s MESTO=<mesto>).
Výstup: public/data/mesta/mapa-<mesto>.json – vrstvy so skupinou, bodmi [lat, lon, názov, {detail}] alebo čiarami,
        a hranice mestských častí (ak sú v portáli).
Spustenie: MESTO=kosice python scripts/zber_mapa_mesta.py

GDPR: z detailu vypúšťame identifikátory (IČO, DIČ), súradnice a interné polia; osobné údaje vo vrstvách nie sú
(zariadenia, školy, zastávky, ihriská). Autori umeleckých diel sú verejne uvádzaní pri dielach.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from spolocne import DATA, VEREJNE, bez_diakritiky, s, spusti, zapis_ak_zmena

MESTO = os.environ.get("MESTO", "kosice")
MAX_BODOV = 3000
# skupina podľa názvu datasetu (prvá zhoda), None = vynechať
SKUPINY = [
    (r"adresné body|sodb|cyklosčítač|kvalita ovzdušia|reklamné plochy|^mestské časti$", None),
    (r"volebn", "Voľby 2026"),
    (r"zastávk|cyklist", "Doprava"),
    (r"škol|centrá voľného času", "Školy"),
    (r"sociáln|ubytovn", "Sociálne služby"),
    (r"ihrisk|výbeh|fontán|workout", "Šport a voľný čas"),
    (r"kultúr|turistick|umeleck", "Kultúra a turizmus"),
    (r"strom|chránen", "Príroda"),
    (r"pošt|polícia|zberné dvory|cirkulárn", "Služby mesta"),
]
# pole s názvom – od najkonkrétnejšieho po všeobecné
NAZVY = ["turisticky_ciel_nazov", "poriadkovy_utvar_nazov", "volebna_miestnost_nazov", "zastavka_nazov", "nazov_diela", "nazov_zariadenia", "nazov_ubytovna",
         "objekt_ochrany_nazov", "nazov_font", "nazov_di", "nazov", "name", "názov", "organizacia_nazov", "organizaci", "adresa_naz"]
ULICA = re.compile(r"(^|_)(ulica|uli|ulica_naz|ulica_nazov|adres_ulica)$|^adresa_ulica$|^adresa$|organizacia_adresa$|_adresa_ulica$|adresa_uli$", re.I)
CISLO_O = re.compile(r"orienta|(^|_)ori$|_o_c$", re.I)
CISLO_S = re.compile(r"supisne|(^|_)sup$", re.I)
MC = re.compile(r"mestska_cast|mestska_ca|_m_1$|_m_c$|adresa_m_1", re.I)
ZAHODIT = re.compile(r"psc|(^|_)mesto$|(^|_)mes$|adresa_mes|obec$|^okres$|krajina|(^|_)kra$|zriadovatel_typ|volby_datum|^okres", re.I)
VYNECHAT_POLE = re.compile(r"(^|_)(fid|objectid|object_id|globalid|ico|dic|ic_dph|x|y|lat|lon|latitude|longitude|shape|eduid|zverejnil|datum_aktualizacie|krajina|"
                           r"samosprava|ogc_fid|id_|pasport|foto)", re.I)


def skupina(nazov: str) -> str | None:
    for vzor, sk in SKUPINY:
        if re.search(vzor, nazov, re.I):
            return sk
    return "Ostatné"


def pekne(k: str) -> str:
    t = re.sub(r"^(organizacia|organiza|adresa|poriadkovy_utvar|volebna_miestnost|objekt_ochrany|turisticky_ciel|ubytovna)_?", "", k, flags=re.I)
    t = t.replace("_", " ").strip()
    return (t[:1].upper() + t[1:]) if t else k


def stiahni(url: str) -> list[dict]:
    feat, offset = [], 0
    while True:
        j = s.get(url + "/query", params={"where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "4326", "f": "json",
                                          "resultOffset": offset, "resultRecordCount": 2000}, timeout=180).json()
        if "error" in j:
            raise RuntimeError(j["error"].get("message"))
        d = j.get("features", [])
        feat += d
        if len(d) < 2000 and not j.get("exceededTransferLimit"):
            return feat
        offset += len(d)


def bod(g: dict) -> tuple[float, float] | None:
    if not g:
        return None
    if "x" in g and "y" in g and g["x"] is not None:
        return round(g["y"], 6), round(g["x"], 6)
    if g.get("points"):
        x, y = g["points"][0][:2]
        return round(y, 6), round(x, 6)
    return None


def main() -> int:
    katalog = json.loads((DATA / f"katalog-{MESTO}.json").read_text(encoding="utf-8"))
    vrstvy, hranice = [], None
    for p in katalog["datasety"]:
        for v in p.get("vrstvy") or []:
            geo = (v.get("geometria") or "").replace("esriGeometry", "")
            if not geo or not p.get("sluzba"):
                continue
            url = f"{p['sluzba']}/{v['id']}"
            # hranice mestských častí: polygónová vrstva s 22 (Košice) prvkami
            if geo == "Polygon" and re.search(r"administratívne hranice", p["nazov"], re.I) and (v.get("pocet") or 0) == 22 and hranice is None:
                try:
                    f = s.get(url + "/query", params={"where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "4326", "f": "geojson"}, timeout=180).json()
                    for x in f.get("features", []):
                        pr = x.get("properties") or {}
                        nazov = next((pr[k] for k in ("NM4", "NM5", "NM3") if pr.get(k)), "")
                        x["properties"] = {"n": re.sub(r"^.*?-\s*", "", str(nazov)).strip() or str(nazov)}
                    hranice = {"type": "FeatureCollection", "features": f.get("features", [])}
                    print(f"Hranice: {p['nazov']} ({len(hranice['features'])})")
                except Exception as e:  # noqa: BLE001
                    print("Hranice:", e)
                continue
            sk = skupina(p["nazov"])
            if sk is None or not (1 <= (v.get("pocet") or 0) <= MAX_BODOV) or geo not in ("Point", "Multipoint", "Polyline"):
                continue
            try:
                feat = stiahni(url)
            except Exception as e:  # noqa: BLE001
                print(f"CHYBA {p['nazov']}: {e}")
                continue
            polia = [f[0] for f in v["polia"]]
            alias = {f[0]: f[2] or f[0] for f in v["polia"]}
            male = {k.lower(): k for k in polia}
            klucNazov = next((male[n] for n in NAZVY if n in male), None)
            if geo == "Polyline":
                ciary = [[[round(y, 5), round(x, 5)] for x, y, *_ in path] for f in feat for path in (f.get("geometry") or {}).get("paths", [])]
                vrstvy.append({"id": p["id"][:8] + str(v["id"]), "nazov": p["nazov"], "skupina": sk, "typ": "ciary", "ciary": ciary, "zdroj": f"{katalog['zdroj']}/datasets/{p['id']}"})
                print(f"{sk} | {p['nazov']}: {len(ciary)} čiar")
                continue
            body = []
            for f in feat:
                b = bod(f.get("geometry"))
                if not b or not (47 < b[0] < 50 and 16 < b[1] < 23):
                    continue
                a = f.get("attributes") or {}
                nazov = str(a.get(klucNazov) or "").strip() if klucNazov else ""
                detail = {}
                # pole posudzujeme podľa názvu aj aliasu (skrátené názvy polí ako „organiza_1“ majú alias „Adresa ulica“)
                sn = lambda k: f"{k}|{re.sub(r'[^a-z0-9]+', '_', bez_diakritiky(alias.get(k) or '').lower()).strip('_')}"  # noqa: E731
                je = lambda r, k: bool(r.search(k) or r.search(sn(k).split("|", 1)[1]))  # noqa: E731
                hod = lambda k: str(a.get(k)).strip() if a.get(k) not in (None, "", " ", "None", "null") else ""  # noqa: E731
                ul = next((hod(k) for k in polia if je(ULICA, k) and hod(k)), "")
                co = next((hod(k) for k in polia if je(CISLO_O, k) and hod(k)), "") or next((hod(k) for k in polia if je(CISLO_S, k) and hod(k)), "")
                mc = next((hod(k) for k in polia if je(MC, k) and hod(k)), "")
                mc = re.sub(r"^Mestská časť\s*", "", re.sub(r"^.*Košice\s*-\s*", "", mc)).strip()
                adresa = ", ".join(x for x in [f"{ul} {co}".strip() if ul else "", mc] if x)
                if adresa:
                    detail["Adresa"] = adresa
                for k in polia:
                    if (k == klucNazov or k.lower() in NAZVY or VYNECHAT_POLE.search(k) or VYNECHAT_POLE.search(alias.get(k) or "")
                            or any(je(r, k) for r in (ULICA, CISLO_O, CISLO_S, MC, ZAHODIT)) or re.search(r"^url_|foto", k, re.I)):
                        continue
                    t = hod(k)
                    if not t or t in ("0", "False") or re.fullmatch(r"-?\d{10,}", t):
                        continue
                    if len(detail) < 7:
                        detail[pekne(alias.get(k) or k)] = t[:600 if re.search(r"spadov|popis", k, re.I) else 200]
                body.append([b[0], b[1], nazov or p["nazov"], detail])
            # body na rovnakom mieste s rovnakým názvom zlúčime (napr. volebná miestnosť pre viac skupín ulíc)
            zlucene: dict[tuple, list] = {}
            for b in body:
                k = (b[0], b[1], b[2])
                if k not in zlucene:
                    zlucene[k] = [b[0], b[1], b[2], dict(b[3])]
                    continue
                for kk, vv in b[3].items():
                    stare = zlucene[k][3].get(kk)
                    if stare is None:
                        zlucene[k][3][kk] = vv
                    elif vv not in stare.split("; "):
                        zlucene[k][3][kk] = (stare + "; " + vv)[:900]
            body = list(zlucene.values())
            if body:
                nazov_vrstvy = p["nazov"] + (" – body" if any(x["nazov"] == p["nazov"] for x in vrstvy) or any(f2.get("geometria", "").endswith("Polyline") for f2 in p.get("vrstvy", [])) else "")
                vrstvy.append({"id": p["id"][:8] + str(v["id"]), "nazov": nazov_vrstvy, "skupina": sk, "typ": "body", "body": body, "zdroj": f"{katalog['zdroj']}/datasets/{p['id']}"})
                print(f"{sk} | {p['nazov']}: {len(body)} bodov")
    poradie = [sk for _, sk in SKUPINY if sk] + ["Ostatné"]
    vrstvy.sort(key=lambda v: (poradie.index(v["skupina"]), v["nazov"]))
    if not vrstvy:
        raise RuntimeError("Mapa mesta: žiadne vrstvy")
    zapis_ak_zmena(VEREJNE / "mesta" / f"mapa-{MESTO}.json", {"aktualizovane": datetime.now().isoformat(timespec="seconds"), "zdroj": katalog["zdroj"],
                                                              "hranice": hranice, "vrstvy": vrstvy}, kompaktne=True)
    print(f"Mapa {MESTO}: {len(vrstvy)} vrstiev, {sum(len(v.get('body', [])) for v in vrstvy)} bodov")
    return 0


if __name__ == "__main__":
    spusti(main, "Mapa mesta")
