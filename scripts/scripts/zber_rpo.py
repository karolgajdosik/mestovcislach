"""Dodávatelia mesta a mestských častí v Registri právnických osôb (RPO, Štatistický úrad SR).

Pre IČO najväčších dodávateľov (faktúry, zmluvy magistrátu, zmluvy mestských častí) zistí právnu formu,
dátum vzniku a prípadného zániku a obec sídla. Mená štatutárov ani spoločníkov neukladáme.
Podnikateľov – fyzické osoby (právna forma 1xx okrem obchodných spoločností) označíme, aby ich web nezobrazoval menom.

Zdroj: https://api.statistics.sk/rpo/v1 (otvorené API, bez kľúča).
Výstup: data/rpo-dodavatelia.json  {ico: {nazov, forma, vznik, zanik, obec, fo, overene}}
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta, timezone

from spolocne import DATA, s, spusti

API = "https://api.statistics.sk/rpo/v1"
VYSTUP = DATA / "rpo-dodavatelia.json"
MAX_DOTAZOV = 900  # na jeden beh; zvyšok sa doplní v ďalších dňoch
OBNOVA_DNI = 60


def ica() -> set[str]:
    vysl: set[str] = set()
    for subor in ("faktury-bratislava.json", "zmluvy-bratislava.json", "zmluvy-mc.json"):
        cesta = DATA / subor
        if cesta.exists():
            vysl |= set(re.findall(r'"ico": ?"(\d{6,8})"', cesta.read_text(encoding="utf-8")))
    return {i.zfill(8) for i in vysl}


def platne(zoznam: list | None) -> dict | None:
    if not zoznam:
        return None
    bez_konca = [x for x in zoznam if not x.get("validTo")]
    return (bez_konca or sorted(zoznam, key=lambda x: x.get("validTo", "")))[-1]


def zisti(ico: str) -> dict | None:
    r = s.get(f"{API}/search", params={"identifier": ico}, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    vysledky = r.json().get("results") or []
    if not vysledky:
        return None
    # záznam s najdlhšou platnosťou IČO (bez zániku, inak najneskorší)
    hlavny = sorted(vysledky, key=lambda v: (v.get("termination") is None, v.get("establishment") or ""))[-1]
    e = s.get(f"{API}/entity/{hlavny['id']}", timeout=60)
    e.raise_for_status()
    e = e.json()
    forma = (platne(e.get("legalForms")) or {}).get("value", {})
    adresa = platne(e.get("addresses")) or {}
    obec = re.sub(r"^Bratislava - mestská časť ", "Bratislava-", (adresa.get("municipality") or {}).get("value", ""))
    kod = str(forma.get("code") or "")
    # 101–109 podnikateľ – fyzická osoba (živnostník, SHR, slobodné povolanie)
    fo = kod.startswith("10")
    return {"nazov": None if fo else (platne(e.get("fullNames")) or {}).get("value"), "forma": forma.get("value"), "kod_formy": kod,
            "vznik": e.get("establishment"), "zanik": e.get("termination"), "obec": None if fo else obec, "fo": fo}


def main() -> int:
    data = json.loads(VYSTUP.read_text(encoding="utf-8")) if VYSTUP.exists() else {"dodavatelia": {}}
    dod: dict = data["dodavatelia"]
    hranica = (date.today() - timedelta(days=OBNOVA_DNI)).isoformat()
    poradie = sorted(ica(), key=lambda i: (i in dod, dod.get(i, {}).get("overene", "")))
    dotazy, chyby = 0, 0
    for ico in poradie:
        if dotazy >= MAX_DOTAZOV:
            break
        if ico in dod and dod[ico].get("overene", "") >= hranica:
            continue
        try:
            z = zisti(ico)
            dotazy += 1
            dod[ico] = {**(z or {"nenajdene": True}), "overene": date.today().isoformat()}
            time.sleep(0.2)
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"::warning title=RPO::{ico}: {e}")
            if chyby > 30:
                break
            time.sleep(3)
    print(f"RPO: {len(dod)} dodávateľov, {dotazy} nových dotazov, {chyby} chýb")
    if not dod:
        raise RuntimeError("RPO: žiadne údaje")
    data = {"zdroj": {"nazov": "Register právnických osôb, podnikateľov a orgánov verejnej moci (ŠÚ SR)", "url": "https://rpo.statistics.sk", "licencia": "otvorené údaje"},
            "dodavatelia": dict(sorted(dod.items())), "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    VYSTUP.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    spusti(main, "Zber RPO")
