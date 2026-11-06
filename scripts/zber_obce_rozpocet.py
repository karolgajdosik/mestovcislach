"""Plnenie rozpočtov obcí (Rozpočtový portál MF SR / DataCentrum, rozpocet.sk) → data/obce/rozpocet.json.

Pre obce je k dispozícii len ekonomická klasifikácia (funkčná – školstvo, doprava… – sa pre obce nezverejňuje).
Za posledný ukončený rok sa ukladá skutočnosť:
  príjmy: podielová daň (111), daň z nehnuteľností (121), dane za špecifické služby – poplatky za odpad a pod. (133),
          nedaňové príjmy (200), granty a transfery (300), spolu
  výdavky: mzdy a odvody (610 + 620), tovary a služby (630), bežné transfery (640), úroky (650),
          kapitálové výdavky – investície (700), spolu

ID organizácie obce v portáli sa hľadá podľa názvu (`organizacie/hladajObec`) a zhody kódu obce; ukladá sa do cache.
Zber je priebežný: v jednom behu sa stiahne najviac LIMIT obcí, ktoré ešte nemajú aktuálny rok.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote

import requests

from spolocne import DATA, spusti, zapis_ak_zmena
from zber_obce_temy import OBCE

API = "https://rozpocet.sk/rest/api/"
SUBOR = DATA / "obce" / "rozpocet.json"
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
CAS = 40 * 60  # sekúnd na beh
PRIJMY = {"111": "podielova", "121": "nehnutelnosti", "133": "poplatky", "200": "nedanove", "300": "granty"}
VYDAVKY = {"610": "mzdy", "620": "mzdy", "630": "tovary", "640": "transfery", "650": "uroky", "700": "investicie"}

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; mestovcislach.sk; info@mestovcislach.sk)", "Accept": "application/json"})


def get(cesta: str) -> dict:
    for pokus in range(4):
        try:
            r = s.get(API + cesta, timeout=60)
            if r.status_code == 200 and r.text.startswith("{"):
                return r.json()
            if "Request Rejected" in r.text:
                time.sleep(20 * (pokus + 1))
                continue
            r.raise_for_status()
        except requests.RequestException:
            time.sleep(10 * (pokus + 1))
    raise RuntimeError(f"rozpocet.sk: {cesta}")


def posledny_rok() -> int:
    p = get("rozpocet/poslednaAktualizacia/SAM/SAM/SCH")["payload"]
    return p["rok"] if p.get("mesiac") == 12 else p["rok"] - 1


def org_id(o: dict, rok: int) -> int | None:
    for x in get(f"organizacie/hladajObec/{quote(o['nazov'])}/{rok}").get("payload") or []:
        if str(x.get("kod")) == o["kod"]:
            for p in x.get("podurovne") or []:
                if str(p.get("nazov", "")).startswith(("Obec ", "Mesto ")):
                    return p["id"]
            pod = x.get("podurovne") or []
            return pod[0]["id"] if pod else None
    return None


def polozky(oid: int, rok: int, typ: str, kody: dict) -> dict[str, float]:
    d = get(f"rozpocet/polozkyRozpocetuFilterSamOrg/SK/{oid}/{rok}/SAM/false/{typ}?{typ}={','.join(kody)}")
    out: dict[str, float] = {}
    for x in d.get("payload") or []:
        k = str(x.get("kod"))
        if k in kody:
            v = (x.get("hodnoty") or {}).get("SKUTOCNOST")
            if v is not None:
                out[kody[k]] = out.get(kody[k], 0) + float(v)
    return out


def main() -> int:
    stare = json.loads(SUBOR.read_text(encoding="utf-8")) if SUBOR.exists() else {}
    ids: dict[str, int | None] = stare.get("org", {})
    obce: dict[str, dict] = stare.get("obce", {})
    rok = posledny_rok()
    zac = time.time()
    hotovo = chyby = 0
    for o in sorted(OBCE, key=lambda o: (obce.get(o["kod"], {}).get("rok", 0), o["kod"])):
        if time.time() - zac > CAS or hotovo >= LIMIT:
            break
        kod = o["kod"]
        if obce.get(kod, {}).get("rok") == rok:
            continue
        try:
            if kod not in ids:
                ids[kod] = org_id(o, rok)
            if not ids[kod]:
                continue
            spolu = get(f"rozpocet/rozpocetSamOrg/{ids[kod]}/{rok}/4")["payload"].get("KVARTAL4") or []
            if len(spolu) < 2:
                continue
            pr = polozky(ids[kod], rok, "EKP", {k: v for k, v in PRIJMY.items()})
            vy = polozky(ids[kod], rok, "EKV", VYDAVKY)
            obce[kod] = {"rok": rok, "p": round(spolu[0]["hodnoty"].get("SKUTOCNOST") or 0),
                         "v": round(spolu[1]["hodnoty"].get("SKUTOCNOST") or 0),
                         "pr": {k: round(v) for k, v in pr.items()}, "vy": {k: round(v) for k, v in vy.items()}}
            hotovo += 1
        except Exception as e:  # noqa: BLE001
            chyby += 1
            print(f"  {kod}: {e}")
            if chyby > 50:
                break
        time.sleep(0.3)
    akt = sum(1 for v in obce.values() if v.get("rok") == rok)
    print(f"Rozpočty {rok}: tento beh {hotovo} obcí, chýb {chyby}; spolu {len(obce)} obcí, z toho za {rok}: {akt}; bez ID v portáli {sum(1 for v in ids.values() if not v)}")
    if hotovo == 0 and akt < 2000:
        raise RuntimeError("rozpocet.sk: nič sa nestiahlo")
    zapis_ak_zmena(SUBOR, {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rok": rok,
                           "zdroj": {"nazov": "MF SR – Rozpočtový portál (rozpocet.sk), plnenie rozpočtu obce, ekonomická klasifikácia", "url": "https://rozpocet.sk"},
                           "org": dict(sorted(ids.items())), "obce": dict(sorted(obce.items()))}, kompaktne=True)
    return 0


if __name__ == "__main__":
    spusti(main, "Obce – rozpočty (rozpocet.sk)")
