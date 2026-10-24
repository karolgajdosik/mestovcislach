"""Poskytovatelia sociálnych služieb v Bratislave – Centrálny register MPSVR SR.

Zdroj: data.slovensko.sk – „Centrálny register poskytovateľov sociálnych služieb“,
WFS služba gis.geocloud.gov.sk/geoserver/mpsvrsr (vrstva crpss, WGS84).
Berieme len aktívne služby s miestom poskytovania (bod) v Bratislave.

GDPR: nezverejňujeme telefóny, e-maily, štatutárov ani zodpovedných zástupcov a vynechávame
poskytovateľov, ktorí vyzerajú ako fyzické osoby (zverejňujeme len právnické osoby a samosprávu).

Výstupy:
  public/data/socialne-bratislava.json – body pre mapu
  data/socialne-bratislava.json        – súhrn podľa druhu služby a mestských častí
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from spolocne import DATA, VEREJNE, mc_podla_polohy, s, spusti, zapis_ak_zmena

WFS = "https://gis.geocloud.gov.sk/geoserver/mpsvrsr/ows"
ZDROJ = {"nazov": "MPSVR SR – Centrálny register poskytovateľov sociálnych služieb", "url": "https://data.slovensko.sk/datasety", "licencia": "otvorené dáta (data.slovensko.sk)"}
SKUPINY = {
    "deti": ("Jasle a starostlivosť o deti do 3 rokov", r"deti do troch rokov"),
    "seniori": ("Seniori a opatrovanie", r"senior|opatrovateľ|denný stacionár|domov dôchodcov"),
    "postihnutie": ("Zdravotné postihnutie", r"domov sociálnych služieb|rehabilitačné|podporovan\w+ býval|tlmočníck|sprievodcovsk|predčitateľsk|požičiavan|včasnej intervencie|špecializované zariadenie"),
    "krizova": ("Krízová pomoc a bývanie", r"nocľaháreň|útulok|krízov|nízkoprahov|terénna sociálna|integračné|na pol ceste|núdzového bývania|sociálnej rehabilitácie|komunitné centrum|práčovňa|jedáleň|hygien"),
}
PRAVNICKA = re.compile(
    r"s\.\s?r\.\s?o|spol\.|a\.\s?s\.|n\.\s?o\.|o\.\s?z\.|n\.\s?f\.|z\.\s?p\.\s?o|v\.\s?o\.\s?s|k\.\s?s\.|mestsk\w+ čas|hlavné mesto|samosprávny kraj|cirk|charit|diakoni|kongregáci|\brád\b|spolok|nadáci|únia|liga|zväz|asociáci|domov|zariadeni|centrum|inštitút|spoločnos|organizáci|červený kríž|združeni|zbor|komunit|fond|seniorát|farnos|sestier|bratstv|misi|ústav|stredisko|služby",
    re.I)
FYZICKA = re.compile(r"^[A-ZÁČĎÉÍĽĹŇÓÔŔŠŤÚÝŽ][a-záäčďéíľĺňóôŕšťúýž]+ [A-ZÁČĎÉÍĽĹŇÓÔŔŠŤÚÝŽ][a-záäčďéíľĺňóôŕšťúýž]+(ová)?(,| -|$)")


def skupina(druh: str) -> str:
    for k, (_, r) in SKUPINY.items():
        if re.search(r, druh or "", re.I):
            return k
    return "ostatne"


def nazov(obchodne_meno: str) -> str:
    t = re.split(r",\s*IČO", obchodne_meno or "")[0]
    return t.split(", ")[0].strip()


def stiahni() -> list[dict]:
    vsetko, start = {}, 0
    while True:
        r = s.get(WFS, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "mpsvrsr:crpss",
                               "outputFormat": "application/json", "count": 2000, "startIndex": start, "sortBy": "obchodne_meno"}, timeout=300)
        r.raise_for_status()
        f = r.json().get("features", [])
        for x in f:
            vsetko[x.get("id") or len(vsetko)] = x
        if len(f) < 2000:
            break
        start += len(f)
    return list(vsetko.values())


def main() -> int:
    najdi_mc = mc_podla_polohy()
    features = stiahni()
    if len(features) < 3000:
        raise RuntimeError(f"Register sociálnych služieb: málo záznamov ({len(features)})")
    body, vynechane_fo = [], 0
    for f in features:
        p, g = f["properties"], f.get("geometry") or {}
        if p.get("datum_vymazu") or g.get("type") != "Point":
            continue
        lon, lat = g["coordinates"][:2]
        mc = najdi_mc(lon, lat)
        if not mc:
            continue
        meno = p.get("obchodne_meno") or ""
        verejny = (p.get("poskytovatel") or "") != "neverejný poskytovateľ"
        if not verejny and (not PRAVNICKA.search(meno) or FYZICKA.match(meno.strip())):
            vynechane_fo += 1
            continue
        druh = (p.get("druh_ss") or "").strip()
        web = (p.get("web") or "").strip()
        det = {k: v for k, v in {
            "druh": druh, "forma": p.get("forma"), "kap": p.get("kapacita"), "a": (p.get("adresa_poskytovania") or "").strip(),
            "pre": (p.get("cielova_skupina") or "").strip()[:160] or None, "posk": p.get("poskytovatel"),
            "w": ("https://" + web if web and not web.startswith("http") else web) or None, "mc": mc,
        }.items() if v}
        body.append([round(lat, 5), round(lon, 5), skupina(druh), nazov(meno), det])
    if len(body) < 100:
        raise RuntimeError(f"Málo sociálnych služieb v Bratislave ({len(body)})")
    body.sort(key=lambda b: (b[2], b[3]))

    po_druhu = Counter(b[4]["druh"] for b in body)
    kapacita = defaultdict(int)
    for b in body:
        kapacita[b[4]["druh"]] += int(b[4].get("kap") or 0)
    po_mc: dict = defaultdict(Counter)
    for b in body:
        po_mc[b[4]["mc"]][b[2]] += 1
    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kategorie = {k: v[0] for k, v in SKUPINY.items()} | {"ostatne": "Poradenstvo a ostatné"}
    zapis_ak_zmena(VEREJNE / "socialne-bratislava.json", {"zdroj": ZDROJ, "kategorie": kategorie, "body": body, "aktualizovane": teraz}, kompaktne=True)
    zapis_ak_zmena(DATA / "socialne-bratislava.json", {
        "zdroj": ZDROJ, "kategorie": kategorie, "sluzieb": len(body), "vynechane_fyzicke_osoby": vynechane_fo,
        "skupiny": dict(Counter(b[2] for b in body)),
        "druhy": [{"druh": d, "pocet": n, "kapacita": kapacita[d] or None} for d, n in po_druhu.most_common()],
        "mestske_casti": {m: dict(c) for m, c in sorted(po_mc.items())},
        "aktualizovane": teraz,
    })
    print(f"Sociálne služby v BA: {len(body)} (vynechané fyzické osoby {vynechane_fo}); {po_druhu.most_common(8)}")
    return 0


if __name__ == "__main__":
    spusti(main, "Zber sociálnych služieb")
