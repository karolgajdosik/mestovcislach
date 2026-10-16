"""Kontrola živých zdrojov a čerstvosti dát webu mestovcislach.sk.

Vypíše zoznam problémov do súboru (argument) a skončí s kódom 1, ak nejaký je.
Workflow kontrola.yml potom založí alebo aktualizuje issue „Kontrola webu“ (a zavrie ho, keď je všetko v poriadku).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

WEB = "https://mestovcislach.sk"
UZAVIERKY = "https://services8.arcgis.com/pRlN1m0su5BYaFAS/arcgis/rest/services/Rozkopavky_CSO_view/FeatureServer/0/query"
s = requests.Session()
s.headers["User-Agent"] = "mestovcislach.sk kontrola (github.com/karolgajdosik/mestovcislach)"
problemy: list[str] = []


def over(nazov: str, url: str, test, **kw) -> None:
    for pokus in range(2):
        try:
            r = s.get(url, timeout=45, **kw)
            if r.status_code != 200:
                chyba = f"HTTP {r.status_code}"
            else:
                chyba = test(r)
            if not chyba:
                print(f"OK   {nazov}")
                return
        except Exception as e:  # noqa: BLE001
            chyba = str(e)[:200]
    print(f"CHYBA {nazov}: {chyba}")
    problemy.append(f"**{nazov}** – {chyba} ({url})")


def jcheck(fn):
    def t(r):
        try:
            d = r.json()
        except ValueError:
            return "odpoveď nie je JSON"
        if isinstance(d, dict) and d.get("chyba"):
            return f"chyba: {d['chyba']}"
        return fn(d)
    return t


def zbery(dni: dict[str, int]) -> None:
    """Posledný beh každého zberu dát musí byť úspešný a nie starší ako počet dní (gh CLI, token z workflowu)."""
    for subor, max_dni in dni.items():
        out = subprocess.run(["gh", "run", "list", "--workflow", subor, "--limit", "5", "--json", "conclusion,createdAt,status,url"],
                             capture_output=True, text=True)
        if out.returncode:
            problemy.append(f"**{subor}** – stav behov sa nedá zistiť ({out.stderr.strip()[:120]})")
            continue
        behy = [b for b in json.loads(out.stdout) if b["status"] == "completed"]
        if not behy:
            continue
        posledny = behy[0]
        vek = datetime.now(timezone.utc) - datetime.fromisoformat(posledny["createdAt"].replace("Z", "+00:00"))
        if posledny["conclusion"] != "success":
            problemy.append(f"**Zber {subor}** – posledný beh skončil „{posledny['conclusion']}“ ({posledny['url']})")
        elif vek > timedelta(days=max_dni):
            problemy.append(f"**Zber {subor}** – posledný beh pred {vek.days} dňami")
        print(f"{'OK  ' if posledny['conclusion'] == 'success' and vek <= timedelta(days=max_dni) else 'CHYBA'} zber {subor}: {posledny['conclusion']}, pred {vek.days} d")


def main() -> int:
    over("Úvodná stránka", WEB + "/", lambda r: None if "mesto" in r.text else "nečakaný obsah")
    over("Dunaj (SHMÚ)", WEB + "/api/dunaj", jcheck(lambda d: None if isinstance(d.get("stav"), (int, float)) else "chýba vodný stav"))
    over("Morava (SHMÚ)", WEB + "/api/dunaj?rieka=morava", jcheck(lambda d: None if isinstance(d.get("stav"), (int, float)) else "chýba vodný stav"))
    over("Výstrahy (MeteoAlarm)", WEB + "/api/vystrahy", jcheck(lambda d: None))
    over("Ovzdušie (SHMÚ)", WEB + "/api/ovzdusie", jcheck(lambda d: None if d.get("stanice") else "žiadne stanice"))
    over("Podklady asistenta", WEB + "/data/asistent.json", jcheck(lambda d: None if d.get("temy") else "chýbajú témy"))
    over("Uzávierky (ArcGIS mesta)", UZAVIERKY, jcheck(lambda d: None if "count" in d else f"nečakaná odpoveď: {str(d)[:120]}"),
         params={"where": "1=1", "returnCountOnly": "true", "f": "json"})
    over("Počasie (Open-Meteo)", "https://api.open-meteo.com/v1/forecast", jcheck(lambda d: None if d.get("current") else "chýba current"),
         params={"latitude": 48.1486, "longitude": 17.1077, "current": "temperature_2m"})
    # zbery dát (dni podľa frekvencie workflowu + rezerva); OpenStreetMap (cyklo.yml) nesledujeme – Overpass býva preťažený
    zbery({"zber-dat.yml": 3, "crz.yml": 3, "slovensko.yml": 10, "katalog.yml": 10, "volby.yml": 3, "vystavba.yml": 3})
    Path(sys.argv[1] if len(sys.argv) > 1 else "problemy.md").write_text("\n".join(f"- {p}" for p in problemy), encoding="utf-8")
    print(f"Problémov: {len(problemy)}")
    return 1 if problemy else 0


if __name__ == "__main__":
    sys.exit(main())
