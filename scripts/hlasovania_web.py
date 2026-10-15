"""Hlasovania Mestského zastupiteľstva z webu zastupitelstvo.bratislava.sk (Digitálne zastupiteľstvo).

Otvorené dáta mesta (data.bratislava.sk) končia júnom 2023. Novšie hlasovania sú zverejnené len na webe
zastupiteľstva: pri každom zasadnutí karta „Hlasovania“ (po 15 na stránku) s menami poslancov podľa toho,
ako hlasovali, a pri každom bode programu karta „Hlasovanie“ (priradenie hlasovania k bodu).

Ukladáme len meno poslanca (verejná funkcia) a jeho hlas. Spracované zasadnutia sa ukladajú do
data/hlasovania-web.json, aby sa pri ďalšom behu sťahovali len nové.

Použitie: from hlasovania_web import hlasovania_z_webu; hlasovania_z_webu(od="2023-07-01")
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from html import unescape
from pathlib import Path

import requests

BASE = "https://zastupitelstvo.bratislava.sk"
VOL_OBDOBIA = {"297313": "9"}  # 2022–2026 (ďalšie obdobie sa doplní po voľbách)
CACHE = Path(__file__).resolve().parent.parent / "data" / "hlasovania-web.json"
SKUPINY = [("Z", r"Hlasovali za"), ("P", r"Hlasovali proti"), ("Q", r"Zdržali"), ("N", r"Nehlasovali"), ("A", r"Neprítomn")]
TITULY = re.compile(r"^(et|[A-Za-z]{1,6}\.|[A-Za-z]+\.[A-Za-z.]*)$")

s = requests.Session()
s.headers["User-Agent"] = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"


def get(url: str) -> str:
    for pokus in range(4):
        try:
            r = s.get(url, timeout=60)
            if r.status_code == 200:
                time.sleep(0.25)
                return r.text
        except requests.RequestException:
            pass
        time.sleep(3 * (pokus + 1))
    raise RuntimeError(f"Nepodarilo sa stiahnuť {url}")


def meno(text: str) -> str:
    """„Ing. arch. Mgr. art. Pätoprstá Smatana Elena“ → „Elena Pätoprstá Smatana“."""
    t = unescape(text).split(",")[0]
    slova = [w for w in t.split() if not TITULY.match(w)]
    return " ".join(slova[-1:] + slova[:-1]) if len(slova) > 1 else " ".join(slova)


def kluc_mena(m: str) -> str:
    import unicodedata
    n = unicodedata.normalize("NFD", m.lower())
    return " ".join(sorted("".join(c for c in n if not unicodedata.combining(c)).replace("-", " ").split()))


def parsuj_hlasovania(html: str) -> list[dict]:
    vysl = []
    for blok in re.split(r'<div class="panel panel-window hlasovania', html)[1:]:
        m = re.search(r'id="hlasovanie-(\d+)"', blok)
        c = re.search(r"Hlasovanie číslo\s*(\d+)", blok)
        if not m or not c:
            continue
        pozn = re.search(r"<h6><b>Poznámka:</b>\s*([^<]*)</h6>", blok)
        uz = re.search(r'<h6><b>Uznesenie:</b>\s*<a href="([^"]*)">([^<]*)</a>', blok)
        hlasy: dict[str, list] = {}
        casti = re.split(r'<div class="panel-heading"><span class="fa [^"]*"></span>', blok)[1:]
        for cast in casti:
            kod = next((k for k, vzor in SKUPINY if re.match(vzor, cast)), None)
            if not kod:
                continue
            for pid, nm in re.findall(r'href="https://zastupitelstvo\.bratislava\.sk/((?:\d+-sk/)?[a-z0-9-]+)/"><i[^>]*></i>\s*([^<]+)</a>', cast):
                hlasy[pid] = [kod, meno(nm)]
        bod = re.search(r"/bod-(\d+)/", uz.group(1)) if uz else None
        vysl.append({"id": m.group(1), "cislo": int(c.group(1)), "uznesenie": unescape(uz.group(2)).strip() if uz else None,
                     "bod": int(bod.group(1)) if bod else None, "poznamka": unescape(pozn.group(1)).strip() if pozn else None, "hlasy": hlasy})
    return vysl


def zoznam_zasadnuti(vol_obd: str) -> list[tuple[str, str]]:
    najdene: dict[str, str] = {}
    for strana in range(0, 15):
        html = get(f"{BASE}/zasadnutia/?&volObd={vol_obd}&page={strana}")
        nove = 0
        for url, d in re.findall(r'href="(https://zastupitelstvo\.bratislava\.sk/mestske-zastupitelstvo[^"]*?zasadnutie-(\d{8})[^"/]*/)"', html):
            if url not in najdene:
                najdene[url] = f"{d[4:]}-{d[2:4]}-{d[:2]}"
                nove += 1
        if not nove:
            break
    return sorted(((d, u) for u, d in najdene.items()))


def zasadnutie(url: str) -> dict:
    prva = get(url)
    hlasovania: dict[str, dict] = {}
    # Karta „Hlasovania“ si pamätá zvolenú kartu v session (PHPSESSID): najprv ?rokovanie_tab_X=2, potom ?page=1, 2…
    # (?page=N bez predošlého zvolenia karty vracia program, s parametrom karty vždy prvú stranu)
    tab = re.search(r"rokovanie_tab_(\d+)=", prva)
    if tab:
        strana = get(f"{url}?rokovanie_tab_{tab.group(1)}=2")
        for p in range(1, 40):
            nove = [h for h in parsuj_hlasovania(strana) if h["id"] not in hlasovania]
            if not nove:
                break
            for h in nove:
                hlasovania[h["id"]] = h
            strana = get(f"{url}?page={p}")
    # body programu: názov bodu a hlasovania k nemu
    program = get(f"{url}?rokovanie_tab_{tab.group(1)}=4") if tab else prva
    body = sorted({int(b) for b in re.findall(re.escape(url.replace(BASE, "")) + r"bod-(\d+)/", program + prva)}
                  | {h["bod"] for h in hlasovania.values() if h["bod"] is not None})
    nazvy = {}
    for b in body:
        stranka = get(f"{url}bod-{b}/")
        t = re.search(r"<title>(.*?)</title>", stranka, re.S)
        nazvy[b] = re.sub(r"\s+", " ", unescape(t.group(1))).strip() if t else f"Bod {b}"
        typ = re.search(r"bod-typ-(\d+)=hlasovania", stranka)
        if typ:
            for h in parsuj_hlasovania(get(f"{url}bod-{b}/?bod-typ-{typ.group(1)}=hlasovania")):
                hlasovania.setdefault(h["id"], h)["bod"] = b
    for h in hlasovania.values():
        h["nazov"] = nazvy.get(h["bod"]) if h["bod"] is not None else "Procedurálne hlasovanie (mimo bodu programu)"
    return {"url": url, "verzia": 2, "body": len(body), "hlasovania": sorted(hlasovania.values(), key=lambda h: h["cislo"])}


def hlasovania_z_webu(od: str) -> tuple[list[dict], list[dict]]:
    """Vráti (hlasovania, zasadnutia) pre zasadnutia s dátumom >= od. Hlasovanie: obdobie, datum, poradie, bod, hlasy {meno: kód}."""
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {"zasadnutia": {}}
    dnes = date.today().isoformat()
    vysl, zasadnutia = [], []
    for vol_obd, obd in VOL_OBDOBIA.items():
        for d, url in zoznam_zasadnuti(vol_obd):
            zasadnutia.append({"datum": d, "url": url, "obdobie": obd})
            if d < od or d > dnes:
                continue
            z = cache["zasadnutia"].get(url)
            # zasadnutie sa môže dopĺňať ešte niekoľko týždňov po konaní
            cerstve = (date.fromisoformat(dnes) - date.fromisoformat(d)).days < 30
            neuplne = z and z.get("verzia") != 2  # verzia 2: úplné stránkovanie a poznámky
            if not z or not z["hlasovania"] or cerstve or neuplne:
                try:
                    z = zasadnutie(url)
                    print(f"  {d}: {len(z['hlasovania'])} hlasovaní, {z['body']} bodov")
                    cache["zasadnutia"][url] = z
                except Exception as e:  # noqa: BLE001
                    print(f"::warning title=Hlasovania z webu::{d} {url}: {e}")
                    if not z:
                        continue
            for h in z["hlasovania"]:
                vysl.append({"obdobie": obd, "datum": d, "poradie": h["cislo"], "bod": h["nazov"] or "", "uznesenie": h.get("uznesenie"), "poznamka": h.get("poznamka"),
                             "hlasy": {m: k for k, m in h["hlasy"].values()}, "url": url})
    cache["aktualizovane"] = datetime.now().isoformat(timespec="seconds")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return vysl, zasadnutia


if __name__ == "__main__":
    od = sys.argv[1] if len(sys.argv) > 1 else "2023-07-01"
    h, z = hlasovania_z_webu(od)
    print(len(z), "zasadnutí,", len(h), "hlasovaní")
