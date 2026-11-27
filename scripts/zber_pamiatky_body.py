"""Významné chránené pamiatky obcí so súradnicami – pre 3D prelet (Wikidata, Wikipédia, Wikimedia Commons) → data/obce/pamiatky-body.json.

  Wikidata: položky na Slovensku so stupňom ochrany (P1435) a súradnicami (P625); obec podľa P131 – reťazec nadradených
            celkov sa prejde až po obec / mestskú časť s kódom LAU (P782, posledných 6 číslic = kód obce ŠÚ SR).
  Poradie: počet jazykových verzií (sitelinks), článok na sk.wikipedia, fotka – najviac MAX na obec, aspoň 120 m od seba.
  Text do titulku a na čítanie: prvé vety úvodu článku sk.wikipedia, inak druh stavby + vznik (P571) + stupeň ochrany.
  Fotka: P18 – náhľad 480 px a autor / licencia z Commons (extmetadata).
Ukladajú sa len údaje o pamiatkach (stavby, objekty), žiadne osobné údaje.
"""

from __future__ import annotations

import html as H
import json
import math
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import quote

import requests

from spolocne import DATA, spusti, zapis_ak_zmena

SPARQL = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "mestovcislach.sk (info@mestovcislach.sk) zber pamiatok", "Accept": "application/sparql-results+json"}
MAX = 6
s = requests.Session()
s.headers.update({"User-Agent": UA["User-Agent"]})


def dotaz(q: str) -> list[dict]:
    for pokus in range(4):
        try:
            r = s.get(SPARQL, params={"query": q}, headers=UA, timeout=300)
            if r.status_code == 200:
                return r.json()["results"]["bindings"]
            time.sleep(30 * (pokus + 1))
        except requests.RequestException:
            time.sleep(30 * (pokus + 1))
    raise RuntimeError("Wikidata SPARQL neodpovedá")


qid = lambda u: u.rsplit("/", 1)[-1]  # noqa: E731


def km(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * math.cos(math.radians(a[0])))


def storocie(rok: int) -> str:
    return f"{(rok - 1) // 100 + 1}. storočia"


def vety(text: str, limit: int = 230) -> str:
    """Prvá (prípadne druhá) veta úvodu, bez zátvoriek s výslovnosťou a dátumami."""
    t = re.sub(r"\s*\([^()]*\)", "", text).replace("  ", " ").strip()
    casti = re.split(r"(?<=[a-záäčďéíĺľňóôŕšťúýž0-9\)])\.\s+(?=[A-ZÁÄČĎÉÍĽŇÓÔŔŠŤÚÝŽ])", t)
    out = ""
    for c in casti:
        c = c.strip().rstrip(".")
        if not c:
            continue
        nove = f"{out} {c}." if out else f"{c}."
        if len(nove) > limit and out:
            break
        out = nove
        if len(out) > limit * 0.6:
            break
    return out[: limit + 40]


def main() -> int:
    # 1) administratívne celky s kódom LAU a ich nadradené celky (na prechod reťazca P131)
    celky: dict[str, str] = {}
    for r in dotaz("""SELECT ?u ?lau WHERE { ?u wdt:P17 wd:Q214; wdt:P782 ?lau. }"""):
        m = re.search(r"(\d{6})$", r["lau"]["value"])
        if m:
            celky[qid(r["u"]["value"])] = m.group(1)
    rodic: dict[str, set[str]] = defaultdict(set)
    for r in dotaz("""SELECT ?u ?r WHERE { ?u wdt:P17 wd:Q214; wdt:P131 ?r. FILTER EXISTS { ?x wdt:P131 ?u. ?x wdt:P1435 ?d. } }"""):
        rodic[qid(r["u"]["value"])].add(qid(r["r"]["value"]))
    print(f"Celky s kódom LAU: {len(celky)}, celkov s pamiatkami a nadradeným celkom: {len(rodic)}")

    def obec(u: str, hlbka: int = 0) -> str | None:
        if u in celky:
            return celky[u]
        if hlbka > 4:
            return None
        for r in rodic.get(u, ()):
            k = obec(r, hlbka + 1)
            if k:
                return k
        return None

    # 2) pamiatky so súradnicami
    riadky = dotaz("""SELECT ?p ?pLabel ?pDescription ?c ?u ?img ?sl ?clanok ?vznik ?typLabel ?ochranaLabel WHERE {
      ?p wdt:P17 wd:Q214; wdt:P1435 ?ochrana; wdt:P625 ?c; wdt:P131 ?u; wikibase:sitelinks ?sl.
      OPTIONAL { ?p wdt:P18 ?img. }
      OPTIONAL { ?p wdt:P571 ?vznik. }
      OPTIONAL { ?p wdt:P31 ?typ. }
      OPTIONAL { ?clanok schema:about ?p; schema:isPartOf <https://sk.wikipedia.org/>. }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "sk,cs,en". }
    }""")
    pam: dict[str, dict] = {}
    for r in riadky:
        q = qid(r["p"]["value"])
        x = pam.setdefault(q, {"q": q, "n": r["pLabel"]["value"], "u": set(), "sl": int(r["sl"]["value"]), "typ": set(), "ochr": set()})
        x["u"].add(qid(r["u"]["value"]))
        m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["c"]["value"])
        if m:
            x["p"] = [round(float(m.group(2)), 6), round(float(m.group(1)), 6)]
        if "img" in r:
            x["img"] = r["img"]["value"].rsplit("/", 1)[-1]
        if "clanok" in r:
            x["wiki"] = r["clanok"]["value"]
        if "pDescription" in r:
            x["popis"] = r["pDescription"]["value"]
        if "vznik" in r:
            m2 = re.match(r"(-?\d{4})", r["vznik"]["value"])
            if m2:
                x["rok"] = int(m2.group(1))
        if "typLabel" in r and not re.match(r"Q\d+$", r["typLabel"]["value"]):
            x["typ"].add(r["typLabel"]["value"])
        if "ochranaLabel" in r and not re.match(r"Q\d+$", r["ochranaLabel"]["value"]):
            x["ochr"].add(r["ochranaLabel"]["value"])
    print(f"Pamiatky so súradnicami: {len(pam)}")

    # 3) priradenie k obciam a výber najvýznamnejších
    podla: dict[str, list[dict]] = defaultdict(list)
    for x in pam.values():
        if "p" not in x or re.match(r"Q\d+$", x["n"]):
            continue
        kody = {k for u in x["u"] if (k := obec(u))}
        for k in kody:
            podla[k].append(x)
    vyber: dict[str, list[dict]] = {}
    for k, zoz in podla.items():
        zoz.sort(key=lambda x: (-(x["sl"] + (3 if x.get("wiki") else 0) + (1 if x.get("img") else 0)), x["n"]))
        out: list[dict] = []
        for x in zoz:
            if any(km(x["p"], y["p"]) < 0.12 or x["n"] == y["n"] for y in out):
                continue
            out.append(x)
            if len(out) >= MAX:
                break
        vyber[k] = out
    vybrane = {x["q"]: x for v in vyber.values() for x in v}
    print(f"Obcí s pamiatkami: {len(vyber)}, vybraných pamiatok: {len(vybrane)}")

    # 4) texty z úvodu článkov sk.wikipedia (len vybrané)
    texty: dict[str, str] = {}
    for x in vybrane.values():
        if not x.get("wiki"):
            continue
        nazov = x["wiki"].rsplit("/wiki/", 1)[-1]
        try:
            r = s.get(f"https://sk.wikipedia.org/api/rest_v1/page/summary/{nazov}", timeout=60)
            if r.ok and r.json().get("extract"):
                texty[x["q"]] = vety(r.json()["extract"])
        except requests.RequestException:
            pass
        time.sleep(0.05)
    print(f"Texty z Wikipédie: {len(texty)}")

    # 5) autor a licencia fotiek (Commons, po 50)
    fotky: dict[str, dict] = {}
    subory = sorted({x["img"] for x in vybrane.values() if x.get("img")})
    for i in range(0, len(subory), 50):
        davka = subory[i:i + 50]
        try:
            r = s.post("https://commons.wikimedia.org/w/api.php", data={
                "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 480,
                "titles": "|".join("File:" + requests.utils.unquote(f) for f in davka)}, timeout=120).json()
        except (requests.RequestException, ValueError) as e:
            print(f"  Commons: {type(e).__name__}")
            continue
        for st in (r.get("query", {}).get("pages") or {}).values():
            ii = (st.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata") or {}
            cist = lambda k: re.sub(r"<[^>]+>", "", H.unescape((em.get(k) or {}).get("value", ""))).strip()  # noqa: E731
            if ii.get("thumburl"):
                fotky[st["title"][5:].replace(" ", "_")] = {"u": ii["thumburl"], "a": re.sub(r"\s*[,;]?\s*[\w.+-]+@[\w-]+(\.[\w-]+)+", "", cist("Artist")).strip(" ,;")[:80], "l": cist("LicenseShortName")[:40], "s": ii.get("descriptionurl", "")}
        time.sleep(0.3)
    print(f"Fotky s licenciou: {len(fotky)}")

    obce: dict[str, list] = {}
    for k, v in sorted(vyber.items()):
        zoz = []
        for x in v:
            text = texty.get(x["q"])
            if not text:
                typ = sorted(x["typ"], key=len)[0] if x["typ"] else ""
                vznik = f"z roku {x['rok']}" if x.get("rok") and x["rok"] >= 1700 else f"z {storocie(x['rok'])}" if x.get("rok") and x["rok"] > 0 else ""
                ochr = "národná kultúrna pamiatka" if any("národn" in o.lower() for o in x["ochr"]) else "kultúrna pamiatka" if x["ochr"] else ""
                text = ", ".join(t for t in [typ.capitalize() if typ else "", vznik, ochr] if t)
                text = f"{text}." if text else ""
            f = fotky.get(requests.utils.unquote(x.get("img", "")).replace(" ", "_")) if x.get("img") else None
            zoz.append({"n": x["n"], "p": x["p"], "t": text, "q": x["q"], **({"f": f} if f else {}), **({"w": x["wiki"]} if x.get("wiki") else {})})
        obce[k] = zoz
    if len(obce) < 500:
        raise RuntimeError(f"pamiatky-body: len {len(obce)} obcí")
    zapis_ak_zmena(DATA / "obce" / "pamiatky-body.json", {
        "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "zdroj": {"nazov": "Wikidata (chránené pamiatky so súradnicami), Wikipédia (úvod článku), Wikimedia Commons (fotky)", "url": "https://www.wikidata.org"},
        "obce": obce}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Obce – pamiatky pre prelet (Wikidata)")
