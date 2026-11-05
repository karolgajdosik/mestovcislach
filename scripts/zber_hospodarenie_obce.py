"""Hospodárenie všetkých obcí SR z Registra účtovných závierok (registeruz.sk, otvorené API).

Individuálna účtovná závierka obce (Úč ROPO SFOV): náklady, výnosy, daňové výnosy, prijaté transfery, výsledok
hospodárenia, majetok, záväzky, bankové úvery – posledné roky (od OD_ROKU). Rovnaká metodika ako pri krajských
mestách (zber_hospodarenie.py), aby sa obce dali porovnať.

API je pomalé (~1 s na dopyt, pri rýchlych dopytoch odpája), jedna obec ≈ 10 dopytov. Preto:
  - priebežné úložisko data/obce/hospodarenie.json (aj ID účtovnej jednotky a závierok),
  - časový limit na beh (CAS_MIN), ďalší beh pokračuje; obec sa znova kontroluje po KONTROLA_DNI dňoch,
  - 3 súbežné vlákna.
IČO obcí: data/obce/ico.json (scripts/zber_zmluvy_obce.py).
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

from spolocne import DATA, spusti, zapis_ak_zmena
from zber_hospodarenie import ruz, ukazovatele

VYSTUP = DATA / "obce" / "hospodarenie.json"
OD_ROKU = 2022
CAS_MIN = 100
KONTROLA_DNI = 30
POLIA = ("naklady", "vynosy", "danove_vynosy", "transfery_prijate", "vysledok", "osobne_naklady", "majetok", "zavazky", "bankove_uvery", "financne_ucty")
_zamok = threading.Lock()


def obec(kod: str, ico: str, stare: dict) -> dict:
    z = dict(stare)
    uj = ruz("uctovna-jednotka", id=z["uj"]) if z.get("uj") else {}
    if not uj.get("idUctovnychZavierok"):
        # pod jedným IČO býva viac účtovných jednotiek (prázdne duplicitné záznamy) – berieme tú so závierkami
        ids = ruz("uctovne-jednotky", **{"zmenene-od": "2000-01-01", "ico": ico}).get("id", [])
        if not ids:
            z["kontrola"] = date.today().isoformat()
            z["chyba"] = "nenájdená v RÚZ"
            return z
        kandidati = [(i, ruz("uctovna-jednotka", id=i)) for i in ids]
        z["uj"], uj = max(kandidati, key=lambda x: len(x[1].get("idUctovnychZavierok") or []))
    zav = dict(z.get("zav") or {})
    znamy = set(z.get("videne") or [])
    nove_id = [i for i in (uj.get("idUctovnychZavierok") or []) if i not in znamy]
    # pri prvom spracovaní stačia posledné závierky (ID rastú s časom)
    for zid in sorted(nove_id)[-6:]:
        zz = ruz("uctovna-zavierka", id=zid)
        znamy.add(zid)
        rok = (zz.get("obdobieDo") or "")[:4]
        if zz.get("konsolidovana") or not (zz.get("obdobieDo") or "").endswith("-12") or not rok.isdigit() or int(rok) < OD_ROKU:
            continue
        if rok in zav and (zav[rok][1] or "") >= (zz.get("datumPoslednejUpravy") or ""):
            continue
        zav[rok] = [zid, zz.get("datumPoslednejUpravy") or ""]
        u = ukazovatele(zz)
        if u.get("naklady") and u.get("vynosy"):
            z.setdefault("roky", {})[rok] = {k: u[k] for k in POLIA if k in u}
    z["zav"] = zav
    z["videne"] = sorted(znamy | set(nove_id))  # staršie ID, ktoré sme nečítali, už netreba
    z["kontrola"] = date.today().isoformat()
    z.pop("chyba", None)
    return z


def main() -> int:
    ica: dict[str, str] = json.loads((DATA / "obce" / "ico.json").read_text(encoding="utf-8"))
    ulozene = json.loads(VYSTUP.read_text(encoding="utf-8")) if VYSTUP.exists() else {}
    data: dict[str, dict] = ulozene.get("obce", {})
    hranica = (date.today() - timedelta(days=KONTROLA_DNI)).isoformat()
    # najprv nikdy nespracované, potom najdlhšie nekontrolované
    poradie = sorted(ica, key=lambda k: (k in data, (data.get(k) or {}).get("kontrola") or ""))
    poradie = [k for k in poradie if (data.get(k) or {}).get("kontrola", "") < hranica]
    koniec = time.time() + CAS_MIN * 60
    hotovo, chyby = 0, 0

    def uloz() -> None:
        with _zamok:
            zapis_ak_zmena(VYSTUP, {"aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds"), "od_roku": OD_ROKU,
                                    "zdroj": {"nazov": "Register účtovných závierok – individuálne účtovné závierky obcí", "url": "https://www.registeruz.sk"},
                                    "obce": dict(sorted(data.items()))}, kompaktne=True)

    def prace(kod: str) -> None:
        nonlocal hotovo, chyby
        if time.time() > koniec:
            return
        try:
            v = obec(kod, ica[kod], data.get(kod) or {})
        except Exception as e:  # noqa: BLE001
            with _zamok:
                chyby += 1
            print(f"{kod}: {e}")
            return
        with _zamok:
            data[kod] = v
            hotovo += 1
            n = hotovo
        if n % 100 == 0:
            print(f"  {n} obcí, chyby {chyby}")
            uloz()

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(prace, poradie))
    uloz()
    s_rokmi = sum(1 for v in data.values() if v.get("roky"))
    print(f"Spracované {hotovo} (chyby {chyby}), čaká {max(0, len(poradie) - hotovo)}; obcí s výkazmi {s_rokmi} z {len(ica)}")
    if hotovo == 0 and poradie:
        raise RuntimeError("RÚZ: žiadna obec nespracovaná")
    return 0


if __name__ == "__main__":
    spusti(main, "Hospodárenie obcí (RÚZ)")
