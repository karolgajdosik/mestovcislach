"""OpenStreetMap lokálne: dopyty v štýle Overpass nad stiahnutým výrezom Slovenska (Geofabrik), bez verejného servera Overpass.

Prečo: zberové skripty sa pýtali Overpass API po jednom (mapy miest, časti miest, cyklotrasy, vybavenosť, obce);
behy trvali desiatky minút a padali na preťaženom serveri. Výrez Slovenska (~250 MB, denne aktualizovaný) sa stiahne raz,
`osmium tags-filter` z neho rýchlo vyberie len potrebné kľúče a pyosmium spočíta odpoveď v rovnakom tvare ako Overpass JSON
(`elements` s `lat/lon`, `center`, `geometry`, `members`, `tags`) – skripty preto ďalej pracujú bez zmeny.

Podporovaná podmnožina Overpass QL (čo naše skripty používajú):
  area(3600000000+id)->.x;   area["k"="v"][k2=v2]->.x;   area["ISO3166-1"="SK"][admin_level=2]->.x;
  (nwr|node|way|rel|relation)(area.x)[k=v][k~"re"][k][!k][k!=v];   relation(<id>);
  out center tags; | out geom; | out tags geom; | out;   (aj bez zátvorky únie)
Pri čomkoľvek inom vyhodí NepodporovanyDotaz a skript použije Overpass ako doteraz.
Zdroj: © prispievatelia OpenStreetMap (ODbL), výrez Geofabrik GmbH.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

PBF_URLS = [os.environ["OSM_PBF_URL"]] if os.environ.get("OSM_PBF_URL") else [
    "https://download.geofabrik.de/europe/slovakia-latest.osm.pbf",
    "https://download.openstreetmap.fr/extracts/europe/slovakia-latest.osm.pbf"]
CACHE = Path(os.environ.get("OSM_CACHE", Path.home() / ".cache" / "osm-sk"))
MAX_VEK_H = float(os.environ.get("OSM_MAX_VEK_H", "30"))
AREA_OFFSET = 3600000000
_stiahnutie_zlyhalo = ""


class NepodporovanyDotaz(Exception):
    pass


def zapnute() -> bool:
    return os.environ.get("OSM_LOKALNE", "1") != "0" and shutil.which("osmium") is not None


def pbf() -> Path:
    """Výrez Slovenska – stiahne sa, ak chýba alebo je starší ako MAX_VEK_H hodín (v GitHub Actions ho drží actions/cache)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / "slovakia-latest.osm.pbf"
    if p.exists() and p.stat().st_size > 50_000_000 and time.time() - p.stat().st_mtime < MAX_VEK_H * 3600:
        return p
    global _stiahnutie_zlyhalo
    if _stiahnutie_zlyhalo:  # v tomto behu sa už nepodarilo – neskúšať pri každom dopyte znova
        if p.exists() and p.stat().st_size > 50_000_000:
            return p  # radšej starší výrez než nič
        raise RuntimeError(_stiahnutie_zlyhalo)
    import requests
    tmp = p.with_suffix(".part")
    t0 = time.time()
    chyba = ""
    for url in PBF_URLS:
        for pokus in range(3):
            try:
                with requests.get(url, stream=True, timeout=120, headers={"User-Agent": "mestovcislach.sk (info@mestovcislach.sk)"}) as r:
                    r.raise_for_status()
                    with open(tmp, "wb") as f:
                        for kus in r.iter_content(1 << 20):
                            f.write(kus)
                if tmp.stat().st_size > 50_000_000:
                    break
                chyba = f"{url}: podozrivo malý súbor"
            except Exception as e:  # noqa: BLE001
                chyba = f"{url}: {type(e).__name__}"
            time.sleep(10 * (pokus + 1))
        else:
            continue
        break
    else:
        _stiahnutie_zlyhalo = f"výrez OSM sa nepodarilo stiahnuť ({chyba})"
        if p.exists() and p.stat().st_size > 50_000_000:
            print(f"  {_stiahnutie_zlyhalo} – použijem starší výrez")
            return p
        raise RuntimeError(_stiahnutie_zlyhalo)
    tmp.replace(p)
    print(f"  OSM výrez stiahnutý: {p.stat().st_size / 1e6:.0f} MB za {time.time() - t0:.0f} s")
    return p


# ---------- rozbor dopytu ----------
_BLOK = r'(?:\[(?:"(?:[^"\\]|\\.)*"|[^\]"])*\])'  # [ ... ] aj s ] vnútri úvodzoviek


def _filtre(text: str) -> list[tuple]:
    """Rozbor [k=v][k~"re"][k][!k][k!=v] – hodnoty v úvodzovkách môžu obsahovať aj ] a medzery."""
    out = []
    zvysok = re.sub(_BLOK, "", text).strip()
    if zvysok:
        raise NepodporovanyDotaz(f"filter: {text!r}")
    for blok in re.findall(_BLOK, text):
        vnutro = blok[1:-1].strip()
        m = re.fullmatch(r'(!)?\s*(?:"((?:[^"\\]|\\.)*)"|([^"=~!\s]+))\s*(?:(=|!=|~)\s*(?:"((?:[^"\\]|\\.)*)"|([^"]*?)))?\s*', vnutro)
        if not m:
            raise NepodporovanyDotaz(f"filter: {blok!r}")
        neg, kq, kp, op, vq, vp = m.groups()
        k = kq if kq is not None else kp
        v = vq if vq is not None else (vp.strip() if vp is not None else None)
        if neg:
            out.append(("nie", k, None))
        elif op is None:
            out.append(("ma", k, None))
        elif op == "=":
            out.append(("=", k, v))
        elif op == "!=":
            out.append(("!=", k, v))
        else:
            out.append(("~", k, re.compile(v)))
    return out


def _zhoda(tags, filtre) -> bool:
    for op, k, v in filtre:
        h = tags.get(k)
        if op == "ma" and h is None:
            return False
        if op == "nie" and h is not None:
            return False
        if op == "=" and h != v:
            return False
        if op == "!=" and h == v:
            return False
        if op == "~" and (h is None or not v.search(h)):
            return False
    return True


def rozober(q: str) -> dict:
    q = re.sub(r"\s+", " ", q).strip()
    q = re.sub(r"^\[out:json\](\[timeout:\d+\])?(\[maxsize:\d+\])?;?", "", q).strip()
    m = re.search(r"\bout\s*([a-z ]*);\s*$", q)
    if not m:
        raise NepodporovanyDotaz("chýba out")
    vystup = set(m.group(1).split())
    if not vystup <= {"center", "tags", "geom", "body", "meta"}:
        raise NepodporovanyDotaz(f"out {m.group(1)}")
    telo = q[:m.start()].strip()
    oblasti: dict[str, tuple] = {}
    for am in re.finditer(r"area\((\d+)\)->\.(\w+);", telo):
        oblasti[am.group(2)] = ("id", int(am.group(1)) - AREA_OFFSET)
    for am in re.finditer(r"area(" + _BLOK + r"+)->\.(\w+);", telo):
        oblasti[am.group(2)] = ("tagy", _filtre(am.group(1)))
    telo = re.sub(r"area(\(\d+\)|" + _BLOK + r"+)->\.\w+;", "", telo).strip()
    telo = telo.strip()
    if telo.startswith("(") and telo.endswith(");"):
        telo = telo[1:-2]
    elif telo.startswith("(") and telo.endswith(")"):
        telo = telo[1:-1]
    vybery = []
    for cast in [c.strip() for c in telo.split(";") if c.strip()]:
        rm = re.fullmatch(r"(?:relation|rel)\((\d+)\)", cast)
        if rm:
            vybery.append({"typy": {"r"}, "id": int(rm.group(1)), "oblast": None, "filtre": []})
            continue
        sm = re.fullmatch(r"(nwr|node|way|relation|rel)(?:\(area\.(\w+)\))?(" + _BLOK + r"*)", cast)
        if not sm:
            raise NepodporovanyDotaz(f"príkaz {cast!r}")
        typ, obl, fl = sm.groups()
        if obl and obl not in oblasti:
            raise NepodporovanyDotaz(f"neznáma oblasť {obl}")
        typy = {"nwr": {"n", "w", "r"}, "node": {"n"}, "way": {"w"}, "relation": {"r"}, "rel": {"r"}}[typ]
        f = _filtre(fl)
        if not obl or not any(op in ("=", "~", "ma") for op, *_ in f):
            raise NepodporovanyDotaz("výber bez oblasti alebo bez kladného filtra")
        vybery.append({"typy": typy, "id": None, "oblast": oblasti[obl], "filtre": f})
    if not vybery:
        raise NepodporovanyDotaz("prázdny dopyt")
    return {"vybery": vybery, "vystup": vystup}


# ---------- osmium ----------
def _vyrez(vyrazy: list[str]) -> Path:
    """`osmium tags-filter` – menší súbor len s potrebnými kľúčmi (aj s odkazovanými uzlami a cestami); medzi volaniami sa ukladá."""
    zdroj = pbf()
    kluc = hashlib.sha1(("|".join(sorted(set(vyrazy))) + str(zdroj.stat().st_mtime)).encode()).hexdigest()[:16]
    import tempfile
    cesta = Path(os.environ.get("OSM_TMP", tempfile.gettempdir())) / f"osm-filter-{kluc}.osm.pbf"  # mimo cache výrezu
    if not cesta.exists():
        t0 = time.time()
        subprocess.run(["osmium", "tags-filter", "--overwrite", "-o", str(cesta), str(zdroj), *sorted(set(vyrazy))], check=True, capture_output=True)
        print(f"  osmium tags-filter {len(set(vyrazy))} výrazov: {cesta.stat().st_size / 1e6:.1f} MB za {time.time() - t0:.0f} s")
    return cesta


def _nacitaj(subor: Path) -> tuple[dict, dict, dict]:
    """Uzly (s polohou a tagmi), cesty (geometria + tagy) a relácie (členovia + tagy) z malého výrezu."""
    import osmium
    uzly: dict[int, tuple] = {}
    cesty: dict[int, tuple] = {}
    relacie: dict[int, tuple] = {}

    class H(osmium.SimpleHandler):
        def node(self, n):
            if n.location.valid():
                uzly[n.id] = (n.location.lat, n.location.lon, dict(n.tags) if len(n.tags) else None)

        def way(self, w):
            geo = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
            cesty[w.id] = (geo, dict(w.tags), [nd.ref for nd in w.nodes])

        def relation(self, r):
            relacie[r.id] = ([(m.type, m.ref, m.role) for m in r.members], dict(r.tags))

    H().apply_file(str(subor), locations=True, idx="flex_mem")
    return uzly, cesty, relacie


_cache_oblasti: dict = {}


def _polygon_relacie(rid: int, cesty: dict, relacie: dict):
    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union
    if rid not in relacie:
        return None
    vonk, vnut = [], []
    for typ, ref, rola in relacie[rid][0]:
        if typ == "w" and ref in cesty and len(cesty[ref][0]) >= 2:
            ciara = LineString([(lon, lat) for lat, lon in cesty[ref][0]])
            (vnut if rola == "inner" else vonk).append(ciara)
    if not vonk:
        return None
    pv = unary_union(list(polygonize(unary_union(vonk))))
    if pv.is_empty:
        return None
    if vnut:
        pi = unary_union(list(polygonize(unary_union(vnut))))
        if not pi.is_empty:
            pv = pv.difference(pi)
    return pv


def _oblast(definicia: tuple):
    """Polygón oblasti (shapely, pripravený) podľa id relácie alebo tagov – z výrezu hraníc (boundary=administrative)."""
    kl = repr(definicia)
    if kl in _cache_oblasti:
        return _cache_oblasti[kl]
    from shapely.ops import unary_union
    from shapely.prepared import prep
    uzly, cesty, relacie = _nacitaj_hranice()
    if definicia[0] == "id":
        ids = [definicia[1]]
    else:
        ids = [rid for rid, (_, t) in relacie.items() if _zhoda(t, definicia[1])]
    poly = [p for rid in ids if (p := _polygon_relacie(rid, cesty, relacie)) is not None]
    if not poly:
        raise NepodporovanyDotaz(f"oblasť {definicia} sa vo výreze nenašla")
    g = unary_union(poly)
    # cesty a relácie: musia zasahovať dovnútra oblasti, nestačí, že sa jej dotýkajú (napr. susedné obce za hranicou
    # majú s oblasťou spoločnú hraničnú čiaru) – rovnako ako Overpass; preto test voči oblasti zúženej o ~1 m
    _cache_oblasti[kl] = (prep(g), prep(g.buffer(-0.00001)))
    return _cache_oblasti[kl]


_hranice_data = None


def _nacitaj_hranice():
    global _hranice_data
    if _hranice_data is None:
        _hranice_data = _nacitaj(_vyrez(["r/boundary=administrative"]))
    return _hranice_data


def _vyraz(op: str, k: str, v) -> tuple[int, str]:
    """(selektivita, výraz pre osmium) – čím menšie číslo, tým užší výber."""
    if op == "=":
        return 0, f"{k}={v}"
    if op == "~":
        m = re.fullmatch(r"\^\(([\w:.-]+(?:\|[\w:.-]+)*)\)\$", v.pattern)
        if m:
            return 1, f"{k}={','.join(m.group(1).split('|'))}"
        return 2, k
    return 3, k


def _vyrazy(vybery: list[dict]) -> list[str]:
    out = []
    for v in vybery:
        if v["id"] is not None:
            continue  # konkrétna relácia (hranica mesta) – z výrezu hraníc
        typ = "".join(sorted(v["typy"], key="nwr".index))
        kandidati = [(s + (2 if k == "type" else 0), x) for op, k, h in v["filtre"] if op in ("=", "~", "ma") for s, x in [_vyraz(op, k, h)]]
        out.append(f"{typ}/{min(kandidati, key=lambda x: x[0])[1]}")
    return out


def dopyt(q: str) -> dict:
    """Odpoveď v tvare Overpass JSON: {"elements": [...]}."""
    from shapely.geometry import LineString, Point
    d = rozober(q)
    t0 = time.time()
    vyr = _vyrazy(d["vybery"])
    uzly, cesty, relacie = _nacitaj(_vyrez(vyr)) if vyr else ({}, {}, {})
    geom, center = "geom" in d["vystup"], "center" in d["vystup"]
    vyb: dict[tuple, None] = {}
    for v in d["vybery"]:
        if v["id"] is not None:
            if v["id"] not in _nacitaj_hranice()[2]:
                raise NepodporovanyDotaz(f"relácia {v['id']} nie je administratívna hranica")
            vyb[("rh", v["id"])] = None
            continue
        pripr, vnutro = _oblast(v["oblast"])
        if "n" in v["typy"]:
            for i, (lat, lon, t) in uzly.items():
                if t and _zhoda(t, v["filtre"]) and pripr.contains(Point(lon, lat)):
                    vyb[("n", i)] = None
        if "w" in v["typy"]:
            for i, (g, t, _) in cesty.items():
                if g and _zhoda(t, v["filtre"]):
                    if vnutro.intersects(Point(g[0][1], g[0][0]) if len(g) == 1 else LineString([(lo, la) for la, lo in g])):
                        vyb[("w", i)] = None
        if "r" in v["typy"]:
            for i, (cl, t) in relacie.items():
                if not _zhoda(t, v["filtre"]):
                    continue
                for typ, ref, _ in cl:
                    if typ == "n" and ref in uzly and pripr.contains(Point(uzly[ref][1], uzly[ref][0])):
                        vyb[("r", i)] = None
                        break
                    if typ == "w" and ref in cesty and cesty[ref][0]:
                        g = cesty[ref][0]
                        if vnutro.intersects(Point(g[0][1], g[0][0]) if len(g) == 1 else LineString([(lo, la) for la, lo in g])):
                            vyb[("r", i)] = None
                            break

    def bounds(body):
        la = [p[0] for p in body]
        lo = [p[1] for p in body]
        return {"minlat": min(la), "minlon": min(lo), "maxlat": max(la), "maxlon": max(lo)}

    el = []
    poradie = {"n": 0, "w": 1, "r": 2, "rh": 2}
    for typ, i in sorted(vyb, key=lambda x: (poradie[x[0]], x[1])):
        if typ == "n":
            lat, lon, t = uzly[i]
            e = {"type": "node", "id": i, "lat": lat, "lon": lon}
            if t:
                e["tags"] = t
        elif typ == "w":
            g, t, refs = cesty[i]
            e = {"type": "way", "id": i}
            if geom:
                e["bounds"] = bounds(g)
                e["geometry"] = [{"lat": la, "lon": lo} for la, lo in g]
            if center and g:
                b = bounds(g)
                e["center"] = {"lat": (b["minlat"] + b["maxlat"]) / 2, "lon": (b["minlon"] + b["maxlon"]) / 2}
            if not geom and not center:
                e["nodes"] = refs
            if t:
                e["tags"] = t
        else:
            u2, c2, r2 = (uzly, cesty, relacie) if typ == "r" else _nacitaj_hranice()
            cl, t = r2[i]
            e = {"type": "relation", "id": i}
            body = []
            clenovia = []
            for mt, ref, rola in cl:
                m = {"type": {"n": "node", "w": "way", "r": "relation"}[mt], "ref": ref, "role": rola}
                if mt == "w" and ref in c2:
                    body += c2[ref][0]
                    if geom:
                        m["geometry"] = [{"lat": la, "lon": lo} for la, lo in c2[ref][0]]
                elif mt == "n" and ref in u2:
                    body.append(u2[ref][:2])
                    if geom:
                        m["lat"], m["lon"] = u2[ref][:2]
                clenovia.append(m)
            if body and geom:
                e["bounds"] = bounds(body)
            if center and body:
                b = bounds(body)
                e["center"] = {"lat": (b["minlat"] + b["maxlat"]) / 2, "lon": (b["minlon"] + b["maxlon"]) / 2}
            if geom or not center:
                e["members"] = clenovia
            if t:
                e["tags"] = t
        el.append(e)
    print(f"  OSM lokálne: {len(el)} prvkov za {time.time() - t0:.0f} s")
    return {"version": 0.6, "generator": "mestovcislach osm_lokalne (Geofabrik)", "elements": el}


def skus(q: str) -> dict | None:
    """Lokálna odpoveď, alebo None (vypnuté, nepodporovaný dopyt, chyba) – volajúci potom použije Overpass."""
    if not zapnute():
        return None
    try:
        return dopyt(q)
    except NepodporovanyDotaz as e:
        print(f"  OSM lokálne: nepodporované ({e}) – Overpass")
    except Exception as e:  # noqa: BLE001
        print(f"  OSM lokálne zlyhalo ({type(e).__name__}: {e}) – Overpass")
    return None
