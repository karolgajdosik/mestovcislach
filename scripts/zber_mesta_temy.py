"""Školy, doprava, bezpečnosť, životné prostredie a kultúra krajských miest – Štatistický úrad SR (DATAcube).

Kocky:
  sv5001rr–sv5003rr  materské, základné školy a gymnáziá podľa obcí (počet škôl, žiakov, učiteľov) – vývoj od 1996
  Digitálna mapa škôl MŠVVaM (mapaskol.iedu.sk) – aktuálny stav po školách: typ, žiaci, pedagógovia (aj stredné školy)
  do3701rr, zp3701rr, ku3701rr, st3701rr, sv3701rr  – „… – mestá“ (európsky Urban Audit): autá, obete nehôd,
                     cyklistická sieť, cena lístka MHD, voda, odpad, kultúra, ceny bytov, predškolské zariadenia
  sk3002rr, sk3003rr kriminalita podľa krajov (polícia SR) – mesto samotné sa nesleduje
  om7102rr           obyvatelia krajov (na prepočet kriminality na 1 000 obyvateľov)

Výstup: data/mesta/temy.json  {skoly, mestske, kriminalita}
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone

from spolocne import DATA, KOREN, spusti, zapis_ak_zmena
from zber_mesta import DATACUBE, dimenzie, json_get, norm, patri, rozbal

MESTA = json.loads((KOREN / "src" / "mesta.json").read_text(encoding="utf-8"))
# kocka SOŠ (sv5004rr) má posunuté popisy hodnôt (napr. „učitelia“ = počet žiakov) – stredné školy berieme z mapy škôl
SKOLY = {"ms": "sv5001rr", "zs": "sv5002rr", "gym": "sv5003rr"}
UA = ["do3701rr", "zp3701rr", "ku3701rr", "st3701rr", "sv3701rr"]


def oblasti_mesta(kategorie: list[tuple[str, str]], mesto: str) -> list[str]:
    """Kód celého mesta, ak je v kocke; inak kódy mestských častí (nikdy oboje)."""
    presne = [k for k, n in kategorie if norm(n) == mesto]
    if presne:
        return presne[:1]
    return [k for k, n in kategorie if patri(n, mesto) and norm(n) != mesto and not norm(n).startswith("Okres")]


def skoly() -> dict:
    vysl: dict = {m["slug"]: {} for m in MESTA}
    for druh, kocka in SKOLY.items():
        dims = dimenzie(kocka)
        uzemie = dims[0][1]
        ukaz = dict(next(c for d, c in dims if d.endswith("_ukaz")))
        for m in MESTA:
            kody = oblasti_mesta(uzemie, m["nazov"])
            if not kody:
                continue
            riadky = []
            for i in range(0, len(kody), 4):  # API odmieta príliš veľké výbery (mestské časti po štyroch)
                riadky += rozbal(json_get(f"{DATACUBE}/dataset/{kocka}/{','.join(kody[i:i + 4])}/all/all", params={"lang": "sk"}))
            roky: dict[str, dict] = defaultdict(lambda: defaultdict(float))
            for r in riadky:
                lab = norm(ukaz.get(r[f"{kocka}_ukaz"], ""))
                rok = str(r[f"{kocka}_rok"])
                # súčty za všetkých zriaďovateľov: „… spolu“ (počet), „… spolu - deti/žiaci“; učitelia a triedy sčítame po zriaďovateľoch
                if re.search(r"spolu$", lab) and not re.search(r"1\. - 4\.", lab):
                    roky[rok]["skol"] += r["hodnota"]
                elif re.search(r"spolu - (deti|žiaci)$", lab) and not re.search(r"1\. - 4\.", lab):
                    roky[rok]["ziakov"] += r["hodnota"]
                elif re.search(r"- učitel", lab) and not re.search(r"1\.\s?- 4\.", lab):
                    roky[rok]["ucitelov"] += r["hodnota"]
                elif re.search(r"- triedy$", lab) and not re.search(r"1\.\s?- 4\.", lab):
                    roky[rok]["tried"] += r["hodnota"]
            vysl[m["slug"]][druh] = {rok: {k: round(v) for k, v in x.items()} for rok, x in sorted(roky.items()) if x.get("skol") or x.get("ziakov")}
        print(f"Školy {druh}: " + ", ".join(f"{s} {max(v.get(druh, {'-': 0}))}" for s, v in vysl.items()))
    return vysl


def skoly_mapa() -> dict:
    from zber_skoly_iedu import URL_MAPA, citaj, num, typ
    riadky = citaj(URL_MAPA)
    if len(riadky) < 5000:
        raise RuntimeError(f"Mapa škôl: málo riadkov ({len(riadky)})")
    vysl: dict = {}
    for m in MESTA:
        typy: dict[str, dict] = defaultdict(lambda: {"pocet": 0, "ziaci": 0, "ped": 0.0})
        stredne = []
        for x in riadky:
            obec = re.sub(r"^\d{3}\s?\d{2}\s+", "", (x.get("Obec") or "").strip())
            if not patri(obec, m["nazov"]):
                continue
            t_ = typ(x["Názov"])
            if not t_ or t_ == "ine":
                continue
            if t_ == "ss":
                t_ = "gym" if re.search(r"gym", x["Názov"], re.I) else "sos"
            ziaci, ped = num(x["Počet žiakov"]) or 0, num(x["Počet ped.zam."]) or 0
            typy[t_]["pocet"] += 1
            typy[t_]["ziaci"] += int(ziaci)
            typy[t_]["ped"] += ped
            if t_ in ("gym", "sos") and ziaci:
                stredne.append({"nazov": re.sub(r"\s+", " ", x["Názov"]).strip(), "typ": t_, "ziaci": int(ziaci), "ped": round(ped, 1),
                                "web": (x.get("Web stránka") or "").strip()})
        vysl[m["slug"]] = {"typy": {k: {**v, "ped": round(v["ped"])} for k, v in typy.items()}, "stredne": sorted(stredne, key=lambda s_: -s_["ziaci"])}
    print("Mapa škôl: " + ", ".join(f"{k} {sum(t['pocet'] for t in v['typy'].values())}" for k, v in vysl.items()))
    return vysl


def mestske() -> dict:
    """Urban Audit – každý ukazovateľ ako {názov (jednotka): {rok: hodnota}} pre každé mesto."""
    vysl: dict = {m["slug"]: {} for m in MESTA}
    popisy: dict = {}
    for kocka in UA:
        dims = dimenzie(kocka)
        mena = {d: dict(c) for d, c in dims}
        uzemie = dims[0][1]
        ds = json_get(f"{DATACUBE}/dataset/{kocka}/" + "/".join("all" for _ in dims), params={"lang": "sk"})
        ostatne = [d for d, _ in dims if not re.search(r"_(uzemieua|rok)$", d)]
        for r in rozbal(ds):
            uz = norm(mena[dims[0][0]].get(r[dims[0][0]], ""))
            m = next((x for x in MESTA if x["nazov"] == uz), None)
            if not m:
                continue
            casti = [norm(mena[d].get(r[d], "")) for d in ostatne]
            casti = [c for c in casti if c and c != "None" and c != "Muži a ženy spolu"]
            if any(c in ("Muži", "Ženy") for c in casti):
                continue
            kluc = f"{kocka}:" + " | ".join(casti)
            popisy[kluc] = " – ".join(casti)
            vysl[m["slug"]].setdefault(kluc, {})[str(r[f"{kocka}_rok"])] = r["hodnota"]
        print(f"{kocka}: {len(popisy)} ukazovateľov spolu")
    return {"popisy": popisy, "mesta": vysl}


def kriminalita() -> dict:
    kraje = sorted({m["kraj"] for m in MESTA})
    vysl: dict = {"kraje": {}, "obyvatelia": {}}
    for kocka in ("sk3002rr", "sk3003rr"):
        dims = dimenzie(kocka)
        mena = {d: dict(c) for d, c in dims}
        kody = [k for k, n in dims[0][1] if norm(n) in kraje]
        ds = json_get(f"{DATACUBE}/dataset/{kocka}/{','.join(kody)}/all/all/all", params={"lang": "sk"})
        for r in rozbal(ds):
            kraj = norm(mena[dims[0][0]][r[dims[0][0]]])
            druh = norm(mena[f"{kocka}_dim1"][r[f"{kocka}_dim1"]]).replace("(z toho:) ", "")
            if kocka == "sk3003rr" and druh != "Spolu":
                druh = f"{druh} trestné činy"
            elif kocka == "sk3003rr":
                druh = "Trestné činy spolu"
            vysl["kraje"].setdefault(kraj, {}).setdefault(druh, {})[str(r[f"{kocka}_rok"])] = r["hodnota"]
    # obyvatelia krajov (stav k 31. 12.) – rokový rozmer spoznáme podľa štvormiestnych rokov
    dims = dimenzie("om7102rr")
    mena = {d: dict(c) for d, c in dims}
    d_rok = next(d for d, c in dims if c and all(re.fullmatch(r"\d{4}", str(k)) for k, _ in c))
    kody = [k for k, n in dims[0][1] if norm(n) in kraje]
    cesta = [",".join(kody)] + ["all" for _ in dims[1:]]
    for r in rozbal(json_get(f"{DATACUBE}/dataset/om7102rr/" + "/".join(cesta), params={"lang": "sk"})):
        popisy = [norm(mena[d].get(r[d], "")) for d, _ in dims[1:] if d != d_rok]
        if any(re.fullmatch(r"muži|ženy", p_, re.I) for p_ in popisy) or any(re.search(r"stredn|prírastok|úbytok", p_, re.I) for p_ in popisy):
            continue
        kraj = norm(mena[dims[0][0]][r[dims[0][0]]])
        rok = str(r[d_rok])
        vysl["obyvatelia"].setdefault(kraj, {})[rok] = max(r["hodnota"], vysl["obyvatelia"].get(kraj, {}).get(rok, 0))
    print("Kriminalita: " + ", ".join(f"{k} {max(v.get('Trestné činy spolu', {'-': 0}).items())}" for k, v in vysl["kraje"].items()))
    return vysl


def main() -> int:
    p = DATA / "mesta" / "temy.json"
    stare = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    vystup = {"zdroj": {"nazov": "Štatistický úrad SR – DATAcube", "url": "https://datacube.statistics.sk"}}
    chyby = 0
    for kluc, f in (("skoly", skoly), ("skoly_mapa", skoly_mapa), ("mestske", mestske), ("kriminalita", kriminalita)):
        try:
            vystup[kluc] = f()
        except Exception as e:  # noqa: BLE001
            chyby += 1
            import traceback
            traceback.print_exc()
            print(f"::warning title=Témy miest {kluc}::{e!r}")
            vystup[kluc] = stare.get(kluc)
    if chyby == 4:
        raise RuntimeError("Témy miest: všetky moduly zlyhali")
    vystup["aktualizovane"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zapis_ak_zmena(p, vystup)
    return 0


if __name__ == "__main__":
    spusti(main, "Témy miest (DATAcube)")
