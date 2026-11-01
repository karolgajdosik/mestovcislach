"""Strážca návrhov rozpočtov krajských miest na budúci rok → data/rozpocty-<rok>.json.

Mestá zverejňujú návrh rozpočtu najmenej 15 dní pred schválením (§ 9 ods. 2 zákona č. 583/2004 Z. z.),
zvyčajne v novembri, schvaľuje sa v decembri. Nie je to štruktúrovaný údaj – sú to PDF na webe mesta, preto
skript len hľadá dokumenty a pamätá si, kedy ich prvýkrát videl:
  - weby na WordPresse: hľadanie v médiách (/wp-json/wp/v2/media?search=…),
  - ostatné: odkazy na stránke rozpočtu a na úradnej tabuli (aj RSS),
dokument sa započíta, keď názov alebo adresa obsahuje „rozpo…“ a sledovaný rok.
Ukladá len názov dokumentu, odkaz a dátum – žiadne osobné údaje.

Spustenie: python scripts/zber_rozpocty.py [rok]   (predvolený = budúci rok)
"""

from __future__ import annotations

import html
import re
import sys
from datetime import date, datetime, timezone
from urllib.parse import urljoin

from spolocne import DATA, s, spusti, zapis_ak_zmena

ROK = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year + 1
UA = {"User-Agent": "Mozilla/5.0 (compatible; mestovcislach.sk; +https://mestovcislach.sk)"}

# zdroje podľa mesta: ("wp", základ webu) | ("stranka", url) | ("rss", url)
ZDROJE: dict[str, list[tuple[str, str]]] = {
    "bratislava": [("rss", "https://www.bratislava.sk/api/official-board-feed"), ("stranka", "https://zastupitelstvo.bratislava.sk/")],
    "trnava": [("stranka", "https://www.trnava.sk/stranka/rozpocet-a-zaverecny-ucet"), ("stranka", "https://www.trnava.sk/uradna-tabula")],
    "trencin": [("wp", "https://trencin.sk"), ("stranka", "https://trencin.sk/samosprava/transparentny-trencin/uradna-tabula/")],
    "nitra": [("wp", "https://nitra.sk"), ("stranka", "https://nitra.sk/rozpocet-zaverecny-ucet-a-rozpoctove-pravidla/")],
    "zilina": [("wp", "https://zilina.sk"), ("stranka", "https://zilina.sk/mesto-zilina/transparentne-mesto/uradna-tabula/")],
    "banska-bystrica": [("wp", "https://www.banskabystrica.sk"), ("stranka", "https://www.banskabystrica.sk/samosprava/rozpocet-mesta/"),
                        ("stranka", "https://egov.banskabystrica.sk/default.aspx?NavigationState=610:0:")],
    # presov.sk je za overením hCaptcha (neobchádzame) – rozpočet a úradná tabuľa sú aj na egov.presov.sk
    "presov": [("stranka", "https://egov.presov.sk/Default.aspx?NavigationState=440:0:"), ("stranka", "https://egov.presov.sk/Default.aspx?NavigationState=610:0:")],
    "kosice": [("stranka", "https://www.kosice.sk/mesto/ekonomika"), ("stranka", "https://www.kosice.sk/clanky/skupina/uradna-tabula")],
}


def je_rozpocet(text: str) -> bool:
    t = re.sub(r"/20\d\d/\d\d/", "/", text.lower())  # priečinok nahratia vo WordPresse (…/2027/01/…) nie je rok rozpočtu
    # rok ako začiatok obdobia („na rok 2027“, „2027 – 2029“), nie koniec viacročného rozpočtu („2025 – 2027“)
    rok = re.search(rf"(?<!\d)(?<!\d\d\d\d[-–_ ])(?<!\d\d\d\d [-–] )(?<!\d\d\d\d_){ROK}(?!\d)", t)
    # rozpočet na predchádzajúci rok „s výhľadom na roky 2027 – 2028“ – v názve je aj rok ROK-1
    predch = re.search(rf"(?<!\d){ROK - 1}(?!\d)", t)
    return (bool(re.search(r"rozpo[cč]|rozpocet|rozpoctu", t)) and bool(rok) and not predch
            and not re.search(r"participat|dotáci|dotaci|grant|monitorova|plneni|zmena|zmenu|opatren", t))


def druh(text: str) -> str:
    t = text.lower()
    if re.search(r"stanovisk", t):
        return "stanovisko hlavného kontrolóra"
    if re.search(r"n[aá]vrh", t):
        return "návrh rozpočtu"
    if re.search(r"schv[aá]len|uznesen", t):
        return "schválený rozpočet"
    return "dokument k rozpočtu"


def wp(zaklad: str, zhoda=None, hladaj=None, typy=("media",)) -> list[dict]:
    zhoda = zhoda or je_rozpocet
    out = []
    for typ in typy:
      for q in hladaj or (f"rozpočet {ROK}", f"rozpočtu {ROK}", f"rozpoctu {ROK}", f"rozpocet {ROK}"):
        r = s.get(f"{zaklad}/wp-json/wp/v2/{typ}", params={"search": q, "per_page": 50, "orderby": "date"}, headers=UA, timeout=60)
        if r.status_code != 200 or not r.text.lstrip().startswith("["):
            continue
        for x in r.json():
            nazov = html.unescape(re.sub(r"<[^>]+>", "", x.get("title", {}).get("rendered", ""))).strip()
            url = x.get("source_url") or x.get("link") or ""
            obsah = html.unescape(re.sub(r"<[^>]+>", " ", (x.get("content") or {}).get("rendered", "") if typ == "posts" else ""))[:3000]
            if zhoda(f"{nazov} {url} {obsah}"):
                out.append({"nazov": nazov or url.rsplit("/", 1)[-1], "url": url, "datum": (x.get("date") or "")[:10], "text": obsah})
    return out


def stranka(url: str, zhoda=None, **_) -> list[dict]:
    zhoda = zhoda or je_rozpocet
    r = s.get(url, headers=UA, timeout=60)
    if r.status_code != 200:
        print(f"  {url}: HTTP {r.status_code}")
        return []
    out = []
    for m in re.finditer(r'<a\b[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', r.text, re.S | re.I):
        text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        odkaz = urljoin(url, html.unescape(m.group(1)))
        if zhoda(f"{text} {odkaz}"):
            out.append({"nazov": text or odkaz.rsplit("/", 1)[-1], "url": odkaz, "datum": ""})
    return out


def rss(url: str, zhoda=None, **_) -> list[dict]:
    zhoda = zhoda or je_rozpocet
    r = s.get(url, headers=UA, timeout=60)
    if r.status_code != 200:
        print(f"  {url}: HTTP {r.status_code}")
        return []
    out = []
    for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
        g = lambda tag: html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", (re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S) or [None, ""])[1])).strip()
        if zhoda(f"{g('title')} {g('description')}"):
            try:
                d = datetime.strptime(g("pubDate")[:16], "%a, %d %b %Y").date().isoformat()
            except ValueError:
                d = ""
            out.append({"nazov": g("title"), "url": g("link"), "datum": d, "text": g("description")})
    return out


# ---------- ustanovujúce zasadnutia nových zastupiteľstiev (do 30 dní od volieb) ----------
MESIACE = {"januára": 1, "februára": 2, "marca": 3, "apríla": 4, "mája": 5, "júna": 6, "júla": 7, "augusta": 8, "septembra": 9, "októbra": 10, "novembra": 11, "decembra": 12}
VOLBY = date(2026, 10, 24)


def je_ustanovujuce(text: str) -> bool:
    return bool(re.search(r"ustanovuj", text, re.I)) and bool(re.search(r"zasadnut|zastupite", text, re.I))


def datum_zasadnutia(text: str) -> str | None:
    """Prvý dátum v texte medzi voľbami a koncom roka („17. 11. 2026“, „17. novembra 2026“)."""
    kand = []
    for m in re.finditer(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)", text):
        kand.append((int(m.group(3)), int(m.group(2)), int(m.group(1))))
    for m in re.finditer(r"(\d{1,2})\.\s*(" + "|".join(MESIACE) + r")\s*(20\d\d)", text, re.I):
        kand.append((int(m.group(3)), MESIACE[m.group(2).lower()], int(m.group(1))))
    for r_, m_, d_ in kand:
        try:
            x = date(r_, m_, d_)
        except ValueError:
            continue
        if VOLBY < x <= date(2026, 12, 31):
            return x.isoformat()
    return None


def zasadnutia() -> None:
    cesta = DATA / "zasadnutia-ustanovujuce-2026.json"
    import json
    stare = json.loads(cesta.read_text(encoding="utf-8")) if cesta.exists() else {}
    dnes = date.today().isoformat()
    mesta = {}
    for slug, zdroje in ZDROJE.items():
        predtym = {d["url"]: d for d in stare.get("mesta", {}).get(slug, [])}
        najdene: dict[str, dict] = {}
        for typ, url in zdroje:
            try:
                kw = {"zhoda": je_ustanovujuce}
                if typ == "wp":
                    kw.update(hladaj=("ustanovujúce zasadnutie", "ustanovujuce zasadnutie", "ustanovujúceho"), typy=("posts", "media"))
                for d in {"wp": wp, "stranka": stranka, "rss": rss}[typ](url, **kw):
                    # bez dátumu zverejnenia berieme len dokumenty s rokom 2026 (staré pozvánky z 2022 na stránkach ostávajú)
                    if (d["datum"] >= VOLBY.isoformat()) if d.get("datum") else ("2026" in f"{d['nazov']} {d.get('text', '')} {d['url']}"):
                        najdene.setdefault(d["url"], d)
            except Exception as e:  # noqa: BLE001
                print(f"  {slug} {typ}: {type(e).__name__}")
        for u, d in predtym.items():
            najdene.setdefault(u, d)
        zoz = []
        for u, d in najdene.items():
            termin = d.get("termin") or datum_zasadnutia(f"{d['nazov']} {d.get('text', '')} {u}")
            zoz.append({"nazov": d["nazov"][:200], "url": u, "termin": termin, "videne_od": predtym.get(u, {}).get("videne_od", dnes)})
        mesta[slug] = sorted(zoz, key=lambda x: (x["termin"] is None, x["termin"] or ""))
        print(f"{slug}: ustanovujúce zasadnutie {next((x['termin'] for x in mesta[slug] if x['termin']), '–')} ({len(zoz)} dokumentov)")
    zapis_ak_zmena(cesta, {"mesta": mesta, "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="minutes")})


def main() -> int:
    cesta = DATA / f"rozpocty-{ROK}.json"
    stare = {}
    if cesta.exists():
        import json
        stare = json.loads(cesta.read_text(encoding="utf-8"))
    dnes = date.today().isoformat()
    mesta = {}
    for slug, zdroje in ZDROJE.items():
        predtym = {d["url"]: d for d in stare.get("mesta", {}).get(slug, {}).get("dokumenty", [])}
        najdene: dict[str, dict] = {}
        chyby = []
        for typ, url in zdroje:
            try:
                for d in {"wp": wp, "stranka": stranka, "rss": rss}[typ](url):
                    najdene.setdefault(d["url"], d)
            except Exception as e:  # noqa: BLE001
                chyby.append(f"{typ}: {type(e).__name__}")
        # raz nájdený dokument si pamätáme (stránky sa menia), dátum prvého výskytu
        for u, d in predtym.items():
            if je_rozpocet(f"{d['nazov']} {u}"):  # po spresnení pravidiel vypadnú staré omyly
                najdene.setdefault(u, d)
        # dokument nahratý pred polovicou predchádzajúceho roka nie je návrh na sledovaný rok
        najdene = {u: d for u, d in najdene.items() if not d.get("datum") or d["datum"] >= f"{ROK - 1}-06-01"}
        dok = []
        for u, d in najdene.items():
            dok.append({"nazov": d["nazov"][:200], "url": u, "druh": druh(d["nazov"] + " " + u),
                        "zverejnene": d.get("datum") or "", "videne_od": predtym.get(u, {}).get("videne_od", dnes)})
        dok.sort(key=lambda d: (d["zverejnene"] or d["videne_od"]), reverse=True)
        mesta[slug] = {"dokumenty": dok, **({"chyby": chyby} if chyby else {})}
        print(f"{slug}: {len(dok)} dokumentov{' (chyby: ' + ', '.join(chyby) + ')' if chyby else ''}")
    zapis_ak_zmena(cesta, {"rok": ROK, "mesta": mesta, "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="minutes")})
    if date.today() <= date(2026, 12, 31):
        zasadnutia()
    return 0


if __name__ == "__main__":
    spusti(main, "Rozpočty miest")
