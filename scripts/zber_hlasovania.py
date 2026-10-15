"""Hlasovania poslancov a poslankýň Mestského zastupiteľstva hlavného mesta (od roku 2014).

Zdroj: data.bratislava.sk – „Hlasovania poslancov a poslankýň Mestského zastupiteľstva od roku 2014“
(tabuľka: volebné obdobie, zasadnutie, bod, dátum, meno, poslanecký klub, hlasovanie) a
„Zasadnutia orgánov samosprávy“ (odkazy na zápisnice a uznesenia). Licencia CC BY 4.0.

Zverejňujeme len to, čo mesto zverejňuje o výkone verejnej funkcie: meno, klub a hlasovanie.
Číslo hlasovacej karty, kontakty ani iné osobné údaje neukladáme.

Výstupy:
  data/hlasovania-msz.json        – súhrn: dochádzka, zhoda s väčšinou a klubom, kluby (všetky obdobia)
  public/data/hlasovania-msz.json – aktuálne obdobie: každé hlasovanie s hlasmi všetkých poslancov
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from spolocne import DATA, VEREJNE, s, spusti, zapis_ak_zmena

ITEM = "4033a9020d18471095b928b81239f80d"
ZASADNUTIA = "7b0fe912679644c0b6c740eb83107c30"
ZDROJ = {"nazov": "Hlasovania poslancov a poslankýň Mestského zastupiteľstva od roku 2014", "url": f"https://data.bratislava.sk/datasets/{ITEM}", "licencia": "CC BY 4.0"}
# Z = za, P = proti, Q = zdržal(a) sa, N = prítomný, nehlasoval, A = neprítomný
OBDOBIA = {"7": "2014–2018", "8": "2018–2022", "9": "2022–2026"}
KODY = [("Z", r"^za"), ("P", r"^proti"), ("Q", r"zdrž"), ("A", r"neprít|nepríd|ospraved"), ("N", r"nehlas")]


def vrstva(item: str) -> str:
    it = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{item}", params={"f": "json"}, timeout=60).json()
    url = it["url"].rstrip("/")
    return url if url[-1].isdigit() else url + "/0"


def vsetko(url: str, polia: str = "*") -> list[dict]:
    riadky, offset = [], 0
    meta = s.get(url, params={"f": "json"}, timeout=60).json()
    krok = min(int(meta.get("maxRecordCount") or 2000), 2000)
    while True:
        r = s.get(url + "/query", params={"where": "1=1", "outFields": polia, "returnGeometry": "false", "orderByFields": "ObjectId",
                                          "resultOffset": offset, "resultRecordCount": krok, "f": "json"}, timeout=180).json()
        if "error" in r:
            raise RuntimeError(r["error"])
        davka = [f["attributes"] for f in r.get("features", [])]
        riadky += davka
        if len(davka) < krok and not r.get("exceededTransferLimit"):
            return riadky
        offset += len(davka)


def kod(h: str) -> str:
    h = (h or "").strip().lower()
    for k, vzor in KODY:
        if re.search(vzor, h):
            return k
    return "?"


def datum(x) -> str:
    if isinstance(x, (int, float)):
        return datetime.fromtimestamp(x / 1000, timezone.utc).strftime("%Y-%m-%d")
    t = str(x or "").strip()
    m = re.match(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", t)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else t[:10]


def main() -> int:
    riadky = vsetko(vrstva(ITEM), "Volebné_obdobie,Zasadnutie,Poradie_hlasovania,Bod,Dátum,Čas,Meno,Priezvisko,Poslanecký_klub,Hlasovanie")
    if len(riadky) < 100000:
        raise RuntimeError(f"Málo hlasovaní ({len(riadky)})")
    print("Hodnoty hlasovania:", Counter((r.get("Hlasovanie") or "").strip() for r in riadky).most_common(12))
    nezname = Counter((r.get("Hlasovanie") or "").strip() for r in riadky if kod(r.get("Hlasovanie")) == "?")
    if sum(nezname.values()) > len(riadky) * 0.02:
        raise RuntimeError(f"Neznáme hodnoty hlasovania: {nezname.most_common(5)}")

    # hlasovanie = (obdobie, zasadnutie, poradie)
    hlasovania: dict[tuple, dict] = {}
    for r in riadky:
        obd = str(r.get("Volebné_obdobie") or "").strip()
        # „Zasadnutie“ je všeobecný text, poradie sa číslujú v každom zasadnutí od 1 → kľúč musí obsahovať dátum
        k = (obd, datum(r.get("Dátum")), int(float(r.get("Poradie_hlasovania") or 0)))
        h = hlasovania.setdefault(k, {"obdobie": obd, "zasadnutie": k[1], "poradie": k[2], "datum": k[1], "cas": str(r.get("Čas") or "")[:5],
                                      "bod": re.sub(r"\s+", " ", str(r.get("Bod") or "")).strip()[:300], "hlasy": {}})
        meno = f"{(r.get('Meno') or '').strip()} {(r.get('Priezvisko') or '').strip()}".strip()
        if meno:
            h["hlasy"][meno] = (kod(r.get("Hlasovanie")), (r.get("Poslanecký_klub") or "").strip())

    obdobia: dict[str, dict] = {}
    for obd in sorted({h["obdobie"] for h in hlasovania.values()}):
        hl = sorted((h for h in hlasovania.values() if h["obdobie"] == obd), key=lambda h: (h["datum"], h["zasadnutie"], h["poradie"]))
        stat: dict[str, Counter] = defaultdict(Counter)
        kluby_poslanca: dict[str, Counter] = defaultdict(Counter)
        jednotnost: dict[str, list] = defaultdict(list)
        for h in hl:
            postoje = Counter(v for v, _ in h["hlasy"].values() if v in "ZPQ")
            vacsina = postoje.most_common(1)[0][0] if postoje else None
            po_kluboch: dict[str, Counter] = defaultdict(Counter)
            for v, klub in h["hlasy"].values():
                if v in "ZPQ" and klub:
                    po_kluboch[klub][v] += 1
            for klub, c in po_kluboch.items():
                if sum(c.values()) >= 2:
                    jednotnost[klub].append(c.most_common(1)[0][1] / sum(c.values()))
            for meno, (v, klub) in h["hlasy"].items():
                st = stat[meno]
                st["hlasovani"] += 1
                st[v] += 1
                kluby_poslanca[meno][klub or "nezaradení"] += 1
                if v in "ZPQ":
                    if vacsina:
                        st["s_vacsinou"] += v == vacsina
                    kc = po_kluboch.get(klub)
                    if klub and kc and sum(kc.values()) >= 2:
                        st["v_klube"] += 1
                        st["s_klubom"] += v == kc.most_common(1)[0][0]
        pct = lambda a, b: round(100 * a / b, 1) if b else None  # noqa: E731
        poslanci = []
        for meno, st in stat.items():
            aktivne = st["Z"] + st["P"] + st["Q"]
            poslanci.append({"meno": meno, "klub": kluby_poslanca[meno].most_common(1)[0][0], "hlasovani": st["hlasovani"],
                             "pritomnost": pct(st["hlasovani"] - st["A"], st["hlasovani"]), "za": st["Z"], "proti": st["P"], "zdrzal": st["Q"],
                             "nehlasoval": st["N"], "nepritomny": st["A"], "zhoda_s_vacsinou": pct(st["s_vacsinou"], aktivne),
                             "zhoda_s_klubom": pct(st["s_klubom"], st["v_klube"])})
        poslanci.sort(key=lambda p: p["meno"].split()[-1])
        obdobia[obd] = {
            "nazov": OBDOBIA.get(obd, obd),
            "zasadnuti": len({h["zasadnutie"] for h in hl}), "hlasovani": len(hl), "od": hl[0]["datum"], "do": hl[-1]["datum"],
            "poslanci": poslanci,
            "kluby": sorted([{"klub": k, "clenov": sum(1 for p in poslanci if p["klub"] == k), "jednotnost": round(100 * sum(v) / len(v), 1)}
                             for k, v in jednotnost.items()], key=lambda k: -k["clenov"]),
        }
        print(f"{obd}: {len(hl)} hlasovaní, {len(poslanci)} poslancov, {obdobia[obd]['zasadnuti']} zasadnutí")

    aktualne = max(obdobia, key=lambda o: obdobia[o]["do"])
    hl = sorted((h for h in hlasovania.values() if h["obdobie"] == aktualne), key=lambda h: (h["datum"], h["zasadnutie"], h["poradie"]))
    mena = [p["meno"] for p in obdobia[aktualne]["poslanci"]]
    verejne = {
        "zdroj": ZDROJ, "obdobie": aktualne, "obdobie_nazov": OBDOBIA.get(aktualne, aktualne), "poslanci": [[p["meno"], p["klub"]] for p in obdobia[aktualne]["poslanci"]],
        "kody": {"Z": "za", "P": "proti", "Q": "zdržal(a) sa", "N": "prítomný, nehlasoval", "A": "neprítomný", "-": "nebol poslancom"},
        # každé hlasovanie: [dátum, zasadnutie, poradie, bod, hlasy v poradí poslancov ako reťazec]
        "hlasovania": [[h["datum"], h["zasadnutie"], h["poradie"], h["bod"], "".join(h["hlasy"].get(m, ("-",))[0] for m in mena)] for h in hl],
    }
    zasadnutia = []
    try:
        for r in vsetko(vrstva(ZASADNUTIA)):
            if "zastupiteľstvo" in (r.get("Orgán_samosprávy") or "").lower():
                zasadnutia.append({"cislo": r.get("Číslo_zasadnutia"), "datum": datum(r.get("Dátum_zasadnutia")), "zapisnica": r.get("Hyperlink_na_zápisnicu"),
                                   "uznesenia": r.get("Hyperlink_na_prijaté_uznesenia"), "vysledky": r.get("Hyperlink_na_výsledky_hlasovani")})
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Zasadnutia::{e}")
    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    zapis_ak_zmena(VEREJNE / "hlasovania-msz.json", {**verejne, "aktualizovane": teraz}, kompaktne=True)
    zapis_ak_zmena(DATA / "hlasovania-msz.json", {"zdroj": ZDROJ, "aktualne_obdobie": aktualne, "obdobia": obdobia,
                                                  "zasadnutia": sorted(zasadnutia, key=lambda z: z["datum"], reverse=True)[:40], "aktualizovane": teraz})
    return 0


if __name__ == "__main__":
    spusti(main, "Zber hlasovaní MsZ")
