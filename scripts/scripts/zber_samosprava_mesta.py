"""Samospráva krajského mesta z jeho portálu otvorených dát: hlasovania poslancov a zmluvy, faktúry, objednávky.

Zatiaľ Košice (opendata.kosice.sk, CC BY 4.0). Spúšťa sa týždenne v katalog.yml.
Nové volebné obdobie (2026–2030) sa nájde samo, keď ho mesto zverejní na portáli (datasety_hlasovani).

GDPR:
  - hlasovania: len meno, poslanecký klub a hlas (verejná funkcia); tituly, tajné hlasovania a ručné hlasy neukladáme,
  - financie: zmluvné strany bez platného IČO alebo bez právnej formy v názve (fyzické osoby, živnostníci,
    nájomcovia bytov) iba započítame do súčtov – ich mená ani predmet nezverejňujeme.

Výstupy:
  data/mesta/samosprava-<slug>.json                 – súhrny pre stránku /<slug>/samosprava a asistenta
  public/data/mesta/hlasovania-<slug>-<obdobie>.json – každé hlasovanie s hlasmi poslancov (vyhľadávanie na stránke)
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from spolocne import DATA, VEREJNE, s, spusti, zapis_ak_zmena

MESTA = {
    "kosice": {
        "portal": "https://opendata.kosice.sk",
        "hlasovania": [("2018-2022", "6165e208f43a43cc824c2fd585c3c599"), ("2022-2026", "10471bb4ff0f47879af2a861f98e34c5")],
        # typ, dataset, stĺpec dátumu, stĺpec sumy
        "financie": [("zmluvy", "6b66219049674794b462b90512081220", "datum_podpisu", "suma_zmluvy"),
                     ("faktúry", "f3fae948601148c9a458e375a572c84c", "datum_prijatia", "suma_faktury"),
                     ("objednávky", "06d4cb2866c54b43bb1997f7edf86f4d", "datum_vystavenia", "suma_objednavky")],
    },
}
def datasety_hlasovani(cfg: dict) -> list[tuple[str, str]]:
    """Známe datasety hlasovaní + nové volebné obdobia, ak ich mesto medzitým zverejnilo (vyhľadávanie na portáli)."""
    zoznam = list(cfg["hlasovania"])
    try:
        r = s.get(f"{cfg['portal']}/api/search/v1/collections/dataset/items", params={"q": "hlasovanie poslancov", "limit": 50}, timeout=60)
        for f in r.json().get("features", []):
            m = re.search(r"Hlasovanie poslancov mestského zastupiteľstva.*?(\d{4})\s*-\s*(\d{4})", (f.get("properties") or {}).get("title", ""))
            nazov = m and f"{m.group(1)}-{m.group(2)}"
            if nazov and int(m.group(1)) >= 2026 and all(n != nazov for n, _ in zoznam):
                zoznam.append((nazov, str(f["id"]).split("_")[0]))
                print(f"Nové volebné obdobie hlasovaní: {nazov}")
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Hľadanie datasetov hlasovaní::{e}")
    return zoznam


KODY = {"ZA": "Z", "PROTI": "P", "ZDRŽAL SA": "Q", "NEHLASOVAL": "N", "NEPRÍTOMNÝ": "A"}
BEZ_KLUBU = re.compile(r"nezaraden", re.I)
PRAVNA_FORMA = re.compile(r"s\.\s?r\.\s?o|spol\.|a\.\s?s\.|k\.\s?s\.|v\.\s?o\.\s?s|n\.\s?o\.|o\.\s?z\.|z\.\s?p\.\s?o|š\.\s?p\.|\bp\.\s?o\.|gmbh|ltd|inc\.|"
                          r"\b(mesto|mestská časť|obec|kraj|ministerstvo|úrad|univerzit\w*|ústav|inštitút|nadácia|fond|cirk\w*|charita|farnosť|zväz|združenie|"
                          r"spolok|klub|komora|banka|poisťov\w*|slovensk\w+|podnik|agentúra|správa|škola|gymnázium|centrum|divadlo|múzeum|knižnica|"
                          r"zariadenie|spoločenstvo|družstvo|organizácia|polícia|zbor|jednota)\b", re.I)


def vrstva(item: str) -> str:
    for p in json.loads((DATA / "katalog-kosice.json").read_text(encoding="utf-8"))["datasety"]:
        if p["id"] == item and p.get("sluzba"):
            return f"{p['sluzba']}/{p['vrstvy'][0]['id']}"
    url = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{item}", params={"f": "json"}, timeout=60).json()["url"].rstrip("/")
    return url if url[-1].isdigit() else url + "/0"


def vsetko(url: str, polia: list[str]) -> list[dict]:
    vysl, offset = [], 0
    while True:
        r = s.get(url + "/query", params={"where": "1=1", "outFields": ",".join(polia), "returnGeometry": "false", "orderByFields": "ObjectId",
                                          "resultOffset": offset, "resultRecordCount": 2000, "f": "json"}, timeout=240).json()
        if "error" in r:
            raise RuntimeError(r["error"])
        f = [x["attributes"] for x in r.get("features", [])]
        vysl += f
        if len(f) < 2000 and not r.get("exceededTransferLimit"):
            return vysl
        offset += len(f)


def den(v) -> date | None:
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, timezone.utc).date()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(v or ""))
    return date(int(m[1]), int(m[2]), int(m[3])) if m else None


def cisty(t) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip()


# ---------- hlasovania ----------

def hlasovania(cfg: dict, slug: str) -> dict:
    obdobia, subory = {}, {}
    for nazov, item in datasety_hlasovani(cfg):
        url = vrstva(item)
        mena_poli = [f["name"] for f in s.get(url, params={"f": "json"}, timeout=60).json().get("fields", [])]
        klub_pole = "poslanec_klub" if "poslanec_klub" in mena_poli else "poslanecky_klub"
        riadky = vsetko(url, ["zasadnutie_cislo", "bod_cislo", "bod_nazov", "hlasovanie_cislo", "hlasovanie_kategoria", "hlasovanie_utajenie",
                              "hlasovanie_datum", "poslanec_meno", "poslanec_priezvisko", klub_pole, "poslanec_hlasoval", "rucny_hlas"])
        if len(riadky) < 1000:
            raise RuntimeError(f"Hlasovania {nazov}: len {len(riadky)} riadkov")
        hl: dict[tuple, dict] = {}
        tajne = set()
        for r in riadky:
            d = den(r.get("hlasovanie_datum"))
            if not d:
                continue
            k = (d.isoformat(), int(r.get("zasadnutie_cislo") or 0), int(r.get("hlasovanie_cislo") or 0))
            if (r.get("hlasovanie_utajenie") or "").lower().startswith("taj"):
                tajne.add(k)
                continue
            kat = cisty(r.get("hlasovanie_kategoria"))
            bod = cisty(r.get("bod_nazov"))
            h = hl.setdefault(k, {"datum": k[0], "zasadnutie": k[1], "poradie": k[2], "hlasy": {},
                                  "bod": (f"{cisty(r.get('bod_cislo'))} {bod}".strip() + (f" ({kat.lower()})" if kat and kat != "Uznesenie" else ""))[:300]})
            meno = f"{cisty(r.get('poslanec_meno'))} {cisty(r.get('poslanec_priezvisko'))}".strip()
            kod = KODY.get(cisty(r.get("poslanec_hlasoval")).upper())
            if meno and kod:
                h["hlasy"][meno] = (kod, cisty(r.get(klub_pole)))
        zoznam = sorted(hl.values(), key=lambda h: (h["datum"], h["poradie"]))
        stat: dict[str, Counter] = defaultdict(Counter)
        kluby_poslanca: dict[str, Counter] = defaultdict(Counter)
        jednotnost: dict[str, list] = defaultdict(list)
        for h in zoznam:
            postoje = Counter(v for v, _ in h["hlasy"].values() if v in "ZPQ")
            vacsina = postoje.most_common(1)[0][0] if postoje else None
            po_kluboch: dict[str, Counter] = defaultdict(Counter)
            for v, klub in h["hlasy"].values():
                if v in "ZPQ" and klub and not BEZ_KLUBU.search(klub):
                    po_kluboch[klub][v] += 1
            for klub, c in po_kluboch.items():
                if sum(c.values()) >= 2:
                    jednotnost[klub].append(c.most_common(1)[0][1] / sum(c.values()))
            for meno, (v, klub) in h["hlasy"].items():
                st = stat[meno]
                st["hlasovani"] += 1
                st[v] += 1
                kluby_poslanca[meno][klub or "Nezaradení"] += 1
                if v in "ZPQ":
                    if vacsina:
                        st["s_vacsinou"] += v == vacsina
                    kc = po_kluboch.get(klub)
                    if kc and sum(kc.values()) >= 2:
                        st["v_klube"] += 1
                        st["s_klubom"] += v == kc.most_common(1)[0][0]
        pct = lambda a, b: round(100 * a / b, 1) if b else None  # noqa: E731
        poslanci = sorted(({"meno": m, "klub": kluby_poslanca[m].most_common(1)[0][0], "hlasovani": st["hlasovani"],
                            "pritomnost": pct(st["hlasovani"] - st["A"], st["hlasovani"]), "za": st["Z"], "proti": st["P"], "zdrzal": st["Q"],
                            "nehlasoval": st["N"], "nepritomny": st["A"], "zhoda_s_vacsinou": pct(st["s_vacsinou"], st["Z"] + st["P"] + st["Q"]),
                            "zhoda_s_klubom": pct(st["s_klubom"], st["v_klube"])} for m, st in stat.items()), key=lambda p: p["meno"].split()[-1])
        obdobia[nazov] = {
            "nazov": nazov.replace("-", "–"), "zasadnuti": len({h["zasadnutie"] for h in zoznam}), "hlasovani": len(zoznam), "tajnych": len(tajne),
            "od": zoznam[0]["datum"], "do": zoznam[-1]["datum"], "poslanci": poslanci,
            "kluby": sorted([{"klub": k, "clenov": sum(1 for p in poslanci if p["klub"] == k), "jednotnost": round(100 * sum(v) / len(v), 1)}
                             for k, v in jednotnost.items()], key=lambda k: -k["clenov"]),
            "zdroj": f"{cfg['portal']}/datasets/{item}",
        }
        mena = [p["meno"] for p in poslanci]
        subory[nazov] = {"obdobie": nazov, "obdobie_nazov": nazov.replace("-", "–"), "poslanci": [[p["meno"], p["klub"]] for p in poslanci],
                         "kody": {"Z": "za", "P": "proti", "Q": "zdržal(a) sa", "N": "prítomný, nehlasoval", "A": "neprítomný", "-": "nebol poslancom"},
                         "hlasovania": [[h["datum"], h["zasadnutie"], h["poradie"], h["bod"], "".join(h["hlasy"].get(m, ("-",))[0] for m in mena)] for h in zoznam]}
        print(f"Hlasovania {nazov}: {len(zoznam)} hlasovaní ({len(tajne)} tajných vynechaných), {len(poslanci)} poslancov")
    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for obd, d in subory.items():
        zapis_ak_zmena(VEREJNE / "mesta" / f"hlasovania-{slug}-{obd}.json", {**d, "aktualizovane": teraz}, kompaktne=True)
    return {"aktualne_obdobie": max(obdobia, key=lambda o: obdobia[o]["do"]), "obdobia": obdobia,
            "subory": {o: f"/data/mesta/hlasovania-{slug}-{o}.json" for o in obdobia}}


# ---------- zmluvy, faktúry, objednávky ----------

def financie(cfg: dict) -> list[dict]:
    vysl = []
    dnes = date.today()
    for typ, item, pole_datum, pole_suma in cfg["financie"]:
        data = vsetko(vrstva(item), ["dodavatel_ICO", "dodavatel_nazov", "predmet", pole_datum, pole_suma, "mena"])
        po_rokoch: dict[int, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0, "fo_pocet": 0, "fo_suma": 0.0})
        dodavatelia: dict[str, dict] = defaultdict(lambda: {"pocet": 0, "suma": 0.0})
        polozky, skryte = [], 0
        for r in data:
            d, suma = den(r.get(pole_datum)), r.get(pole_suma)
            if not d or not isinstance(suma, (int, float)) or (r.get("mena") or "EUR") != "EUR" or not (2005 <= d.year <= dnes.year):
                continue
            ico = re.sub(r"\D", "", str(r.get("dodavatel_ICO") or ""))
            nazov = cisty(r.get("dodavatel_nazov"))
            verejny = 6 <= len(ico) <= 8 and bool(PRAVNA_FORMA.search(nazov)) and "~" not in nazov
            rok = po_rokoch[d.year]
            rok["pocet"] += 1
            rok["suma"] += suma
            if not verejny:
                rok["fo_pocet"] += 1
                rok["fo_suma"] += suma
                skryte += 1
                continue
            ico = ico.zfill(8)
            if d.year >= dnes.year - 2:
                dod = dodavatelia[ico]
                dod["nazov"] = nazov
                dod["pocet"] += 1
                dod["suma"] += suma
            if d >= dnes - timedelta(days=365):
                polozky.append({"datum": d.isoformat(), "dodavatel": nazov, "ico": ico, "suma": round(suma, 2), "popis": cisty(r.get("predmet"))[:200]})
        if not po_rokoch:
            raise RuntimeError(f"{typ}: žiadne použiteľné riadky")
        vysl.append({
            "typ": typ, "zdroj": f"{cfg['portal']}/datasets/{item}", "zaznamov": len(data), "skryte_fyzicke_osoby": skryte,
            "roky": {str(k): {"pocet": v["pocet"], "suma": round(v["suma"]), "fo_pocet": v["fo_pocet"], "fo_suma": round(v["fo_suma"])} for k, v in sorted(po_rokoch.items())},
            "dodavatelia_posledne_3_roky": sorted(({"ico": k, **{x: (round(y) if x == "suma" else y) for x, y in v.items()}} for k, v in dodavatelia.items()),
                                                  key=lambda x: -x["suma"])[:20],
            "najvacsie_12_mesiacov": sorted(polozky, key=lambda x: -x["suma"])[:15],
        })
        print(f"{typ}: {len(data)} záznamov, skryté (fyzické osoby / bez IČO) {skryte}")
    return vysl


def main() -> int:
    chyby = []
    for slug, cfg in MESTA.items():
        vystup = {"mesto": slug, "portal": cfg["portal"], "licencia": "CC BY 4.0"}
        for k, f in (("hlasovania", lambda: hlasovania(cfg, slug)), ("financie", lambda: financie(cfg))):
            try:
                vystup[k] = f()
            except Exception as e:  # noqa: BLE001
                chyby.append(f"{slug} {k}: {e}")
                print(f"::warning title=Samospráva {slug} {k}::{e}")
                stare = DATA / "mesta" / f"samosprava-{slug}.json"
                if stare.exists():  # ponecháme posledné dobré údaje
                    vystup[k] = json.loads(stare.read_text(encoding="utf-8")).get(k)
        if vystup.get("hlasovania") or vystup.get("financie"):
            zapis_ak_zmena(DATA / "mesta" / f"samosprava-{slug}.json", {**vystup, "aktualizovane": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    if len(chyby) >= 2 * len(MESTA):
        raise RuntimeError("; ".join(chyby))
    return 0


if __name__ == "__main__":
    spusti(main, "Samospráva miest")
