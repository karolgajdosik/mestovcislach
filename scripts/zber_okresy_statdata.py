"""Údaje za okresy, ktoré ŠÚ SR nezverejňuje po obciach (na stránke obce sa ukážu ako „okres X“).

  mzda  – np3110rr priemerná mesačná mzda zistená pracoviskovou metódou (podľa miesta práce), všetky odvetvia
  byty  – st3802rr dokončené byty spolu a v rodinných domoch

Bratislava I–V a Košice I–IV sa zlúčia do okresov „Bratislava“ a „Košice“ (ako v zozname obcí):
byty sa sčítajú, mzda je vážená mzdovými prostriedkami (Mzdy a náhrady mzdy / priemerná mzda = počet zamestnancov).

Výstup data/obce/okresy.json: {"mzda": {okres: {rok: €}}, "byty": {okres: {rok: [spolu, v RD]}}, "sr": {...}}
"""

from __future__ import annotations

import csv
import json
import io
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, s, spusti, zapis_ak_zmena
from statdata_obce import B, H, polozky
from zber_obce_temy import OBCE, cislo

OKRESY = {o["okres"] for o in OBCE}


CASTI = {"Bratislava": 5, "Košice": 4}  # okresy mesta, ktoré sa zlučujú – rok len ak sú všetky


def okres(n: str) -> str | None:
    n = re.sub(r"^Okres\s+", "", (n or "").strip())
    n = re.sub(r"^(Bratislava|Košice) [IV]+$", r"\1", n)
    if n == "Slovenská republika":
        return "SR"
    return n if n in OKRESY else None


def riadky(kocka: str, vyber: dict[str, str]) -> list[dict]:
    """Všetky okresy a roky; vyber = {dimenzia: názov položky} – položky sa vyberú na serveri."""
    info = s.get(f"{B}/public/{kocka}/info", headers=H, timeout=60).json()
    dims = info["dimensions"]
    cas = next(d["acronym"] for d in dims if d["type"] == "TIME")
    ost = [d for d in dims if d["acronym"] != cas]
    spec = []
    for d in ost:
        sel = "all"
        if d["acronym"] in vyber:
            pol = {(x.get("nameSk") or "").strip(): x.get("acronym") for x in polozky(kocka, d["id"])}
            sel = pol[vyber[d["acronym"]]]
        spec.append((d["acronym"], sel))
    ctx = next((a for a, sel in spec if sel != "all" and a != "e_nuts14"), None) or next(a for a, _ in spec if a == "e_unit")
    rows = [f"{a},ASC,{sel}" for a, sel in spec if a != ctx]
    ctx_sel = dict(spec)[ctx]
    url = f"{B}/opendata/cube/dataset/{kocka}/rows/" + "~".join(rows) + f"/columns/{cas},ASC,all/context/{ctx},ASC,{ctx_sel}"
    r = s.get(url, params={"type": "CSV", "lang": "SK"}, timeout=600)
    r.raise_for_status()
    c = r.content
    if c[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(c))
        c = z.read(z.namelist()[0])
    out = list(csv.DictReader(io.StringIO(c.decode("utf-8-sig", "replace"))))
    for x in out:
        x["_cas"] = (x.get(cas) or "").strip()
    return out


def mzdy() -> dict:
    pm: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))  # okres -> rok -> [mzdové prostriedky tis. €, zamestnanci, častí]
    priamo: dict[str, dict[str, float]] = defaultdict(dict)
    rr = riadky("np3110rr", {"e_sex": "Spolu", "e_nace2": "Spolu"})
    hodn: dict[tuple, dict[str, float]] = defaultdict(dict)
    for x in rr:
        v = cislo(x.get("hodnota"))
        o = okres(x.get("e_nuts14", ""))
        if v is None or not o:
            continue
        hodn[(x["e_nuts14"].strip(), x["_cas"])][(x.get("e_indic") or "").strip()] = v
    for (n, rok), d in hodn.items():
        o = okres(n)
        mz, fond = d.get("Priemerná mesačná mzda"), d.get("Mzdy a náhrady mzdy")
        if mz is None:
            continue
        if re.search(r"(Bratislava|Košice) [IV]+$", n) and fond:
            a = pm[o][rok]
            a[0] += fond
            a[1] += fond * 1000 / 12 / mz
            a[2] += 1
        else:
            priamo[o][rok] = round(mz)
    for o, d in pm.items():
        for rok, (fond, zam, n) in d.items():
            if zam and n == CASTI.get(o, n):
                priamo[o][rok] = round(fond * 1000 / 12 / zam)
    return {o: dict(sorted(v.items())) for o, v in sorted(priamo.items())}


def byty() -> dict:
    out: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    casti: dict[tuple, set] = defaultdict(set)
    for x in riadky("st3802rr", {"e_apartments": "Spolu"}):
        v = cislo(x.get("hodnota"))
        o = okres(x.get("e_nuts14", ""))
        if v is None or not o:
            continue
        i = 1 if "rodinných domoch" in (x.get("e_indic") or "") else 0
        out[o][x["_cas"]][i] += int(v)
        casti[(o, x["_cas"], i)].add(x["e_nuts14"].strip())
    for (o, rok, i), c in casti.items():  # Bratislava/Košice: rok bez údajov za všetky okresy mesta vynecháme
        if o in CASTI and len(c) < CASTI[o]:
            out[o].pop(rok, None)
    return {o: dict(sorted(v.items())) for o, v in sorted(out.items())}


def nro() -> list[str]:
    """Najmenej rozvinuté okresy – zoznam na stránke MIRRI SR (podstránka pre každý okres)."""
    import unicodedata
    r = s.get("https://mirri.gov.sk/sekcie/regionalny-rozvoj-2/najmenej-rozvinute-okresy/okresy/", timeout=60,
              headers={"User-Agent": "Mozilla/5.0 (compatible; mestovcislach.sk)"})
    r.raise_for_status()
    slugy = set(re.findall(r"/najmenej-rozvinute-okresy/okresy/([a-z-]+)/", r.text)) - {"archiv-nro"}
    slug = lambda n: re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()).strip("-")  # noqa: E731
    out = sorted(o for o in OKRESY if slug(o) in slugy)
    if len(out) < 10 or len(out) < len(slugy) - 1:
        raise RuntimeError(f"NRO: {len(out)} z {len(slugy)} ({sorted(slugy)})")
    return out


NEHODY_ZALOHA = "https://www.minv.sk/lnisdn/statistika/20260218_011722.691_2025-12-MS/statistika/"


def nehody_zdroj() -> str:
    """Najnovšia decembrová mesačná štatistika (…_RRRR-12-MS) zo stránok MV SR; inak známa záloha."""
    najdene = []
    for u in ("https://www.minv.sk/?statistika-dopravnej-nehodovosti", "https://www.minv.sk/?statisticke-ukazovatele-sluzby-dopravnej-policie",
              "https://www.minv.sk/?statistiky-dopravnej-nehodovosti"):
        try:
            r = s.get(u, timeout=60, headers={"User-Agent": "Mozilla/5.0 (compatible; mestovcislach.sk)"})
            najdene += re.findall(r"(https?://www\.minv\.sk/lnisdn/statistika/\d{8}_[\d.]+_(\d{4})-12-MS/statistika/)", r.text)
        except Exception:  # noqa: BLE001
            pass
    return max(najdene, key=lambda x: (x[1], x[0]))[0] if najdene else NEHODY_ZALOHA


def nehody() -> dict:
    """Dopravné nehody za kalendárny rok podľa územných okresov polície (MV SR, ISDN): nehody, usmrtení, ťažko a ľahko zranení.
    Bratislava 1–5 a Košice 1–4 sa sčítajú do okresov Bratislava a Košice."""
    B_ = nehody_zdroj()
    h = {"User-Agent": "Mozilla/5.0 (compatible; mestovcislach.sk)"}
    r = s.get(B_ + "index-public.html", timeout=60, headers=h)
    r.encoding = "utf-8"
    sub = re.findall(r"href='(mesacna/dnvr/dnvr-\d{4}\.html)' title='([^']+)'", r.text)
    rok = re.search(r"_(\d{4})-12-MS", B_).group(1)
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    casti: dict[str, int] = defaultdict(int)
    for href, title in sub:
        m = re.search(r"Územie:\s*([^\n/]+)", title)
        if not m:
            continue
        n = m.group(1).strip()
        n = re.sub(r"^(Bratislava|Košice)\s*-\s*\d$", r"\1", n)
        if n not in OKRESY:
            continue
        x = s.get(B_ + href, timeout=60, headers=h)
        x.encoding = "utf-8"
        bunky = [c.strip() for c in re.sub(r"<[^>]+>", "|", x.text).split("|") if c.strip()]
        try:
            i = bunky.index("Počet nehôd celkom")
            v = [int(bunky[i + k]) for k in (1, 3, 5, 7)]
        except (ValueError, IndexError):
            continue
        o = out[n]
        for k in range(4):
            o[k] += v[k]
        casti[n] += 1
    for n, c in casti.items():
        if n in CASTI and c != CASTI[n]:
            out.pop(n, None)
    print(f"Nehody {rok}: {len(out)} okresov (napr. Detva {out.get('Detva')})")
    if len(out) < 70:
        raise RuntimeError(f"nehody: len {len(out)} okresov")
    return {"rok": rok, "polia": ["nehody", "usmrtení", "ťažko zranení", "ľahko zranení"], "okresy": dict(sorted(out.items())),
            "zdroj": {"nazov": "MV SR – štatistika dopravnej nehodovosti (ISDN), územné okresy", "url": B_ + "index-public.html"}}


def main() -> int:
    mz = mzdy()
    by = byty()
    f0 = DATA / "obce" / "okresy.json"
    stare0 = json.loads(f0.read_text(encoding="utf-8")) if f0.exists() else {}
    try:
        neh = nehody()
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Nehody::{e}")
        neh = stare0.get("nehody")
    try:
        zoz_nro = nro()
        print(f"Najmenej rozvinuté okresy: {len(zoz_nro)} – {', '.join(zoz_nro)}")
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=NRO::{e}")
        f = DATA / "obce" / "okresy.json"
        zoz_nro = json.loads(f.read_text(encoding="utf-8")).get("nro", []) if f.exists() else []
    print(f"Okresy: mzda {len(mz)} (napr. Detva {list(mz.get('Detva', {}).items())[-2:]}), byty {len(by)} (Detva {list(by.get('Detva', {}).items())[-2:]})")
    if len(mz) < 70 or len(by) < 70:
        raise RuntimeError(f"málo okresov: mzda {len(mz)}, byty {len(by)}")
    zapis_ak_zmena(DATA / "obce" / "okresy.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "zdroj": {"nazov": "ŠÚ SR – mzdy pracoviskovou metódou (np3110rr), dokončené byty (st3802rr)", "url": "https://statdata.statistics.sk"},
        "mzda": mz, "byty": by, "nro": zoz_nro, "nehody": neh,
        "nro_zdroj": {"nazov": "MIRRI SR – najmenej rozvinuté okresy", "url": "https://mirri.gov.sk/sekcie/regionalny-rozvoj-2/najmenej-rozvinute-okresy/okresy/"}}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Okresy – mzdy a dokončené byty (ŠÚ SR)")
