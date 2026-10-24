"""Náhľadové obrázky (Open Graph, 1200 × 630) pre zdieľanie stránok na sociálnych sieťach a v aplikáciách.

Spúšťa sa ručne pri zmene stránok: python scripts/og_obrazky.py → public/og/<stránka>.png
Voľby 2026: python scripts/og_obrazky.py volby → public/og/volby-<mesto>.png s víťazom (primátorom) a účasťou,
hneď ako sú v dátach výsledky (volá ho workflow volby.yml po každom zbere; „volby --treba“ len zistí, či je čo kresliť).
Potrebuje Pillow a písmo Inter (inak DejaVu Sans).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

VYSTUP = Path(__file__).resolve().parent.parent / "public" / "og"
STRANKY = {
    "index": ("Bratislava v číslach", "Obyvatelia, rozpočet, doprava, voľby a živé údaje o meste – prehľadne a so zdrojmi"),
    "mestske-casti": ("Mestské časti", "Profil každej zo 17 častí Bratislavy – ľudia, voľby, peniaze, školy, bezpečnosť a klíma"),
    "vystavba": ("Čo sa stavia a za koľko sa býva", "Zámery v posudzovaní EIA na mape, ceny bytov a nové byty v Bratislave"),
    "upozornenia": ("Čo je nové vo vašej štvrti", "Uzávierky, nové stavebné zámery a zmluvy mestskej časti – kanál bez registrácie"),
    "mapa": ("Mapa Bratislavy", "Školy, lekárne, fontány, športoviská, pamiatky, hluk, horúčavy a uzávierky na jednej mape"),
    "obyvatelia": ("Kto žije v Bratislave", "Sčítanie 2021 podľa mestských častí, prognóza do roku 2035, nezamestnanosť"),
    "volby": ("Voľby a hlasovania", "Komunálne voľby 2026, výsledky volieb a ako hlasovali poslanci zastupiteľstva"),
    "financie": ("Financie mesta", "Rozpočet, zmluvy, faktúry, dotácie mestských častí a dlh"),
    "doprava": ("Doprava v Bratislave", "Uzávierky naživo, sčítače áut a cyklistov, MHD, cyklotrasy, nehody"),
    "vybavenost": ("Vybavenosť mesta", "Školy a spádové obvody, škôlky, lekárne, sociálne služby, nabíjanie"),
    "prostredie": ("Životné prostredie", "Dunaj a Morava naživo, ovzdušie, hluk, zeleň, odpad a chránená príroda"),
    "bezpecnost": ("Bezpečnosť a poriadok", "Priestupky, pokuty a udalosti mestskej polície, podnety obyvateľov"),
    "katalog": ("Katalóg dát", "Všetkých 641 datasetov Bratislavy – tabuľky, grafy a stiahnutie CSV"),
}
CERVENA, TEXT, SIVA, POZADIE = (200, 16, 46), (27, 29, 33), (95, 99, 107), (247, 247, 245)


def pismo(rez: str, velkost: int) -> ImageFont.FreeTypeFont:
    for cesta in (f"/usr/share/fonts/opentype/inter/Inter-{rez}.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(cesta).exists():
            return ImageFont.truetype(cesta, velkost)
    return ImageFont.load_default()


def zalom(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, sirka: int) -> list[str]:
    riadky, riadok = [], ""
    for slovo in text.split():
        skuska = f"{riadok} {slovo}".strip()
        if d.textlength(skuska, font=f) <= sirka:
            riadok = skuska
        else:
            riadky.append(riadok)
            riadok = slovo
    return riadky + [riadok]


def obrazok(nazov: str, podtitul: str) -> Image.Image:
    im = Image.new("RGB", (1200, 630), POZADIE)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1200, 12], fill=CERVENA)
    # logo: červený štvorec so stĺpcami + text
    d.rounded_rectangle([80, 80, 152, 152], radius=16, fill=CERVENA)
    for x, y in ((96, 118), (112, 104), (128, 95)):
        d.rounded_rectangle([x, y, x + 9, 138], radius=2, fill="white")
    f_logo = pismo("Bold", 40)
    d.text((172, 92), "mesto", font=f_logo, fill=TEXT)
    x = 172 + d.textlength("mesto", font=f_logo)
    d.text((x, 92), "v", font=f_logo, fill=CERVENA)
    d.text((x + d.textlength("v", font=f_logo), 92), "číslach", font=f_logo, fill=TEXT)
    f_nadpis = pismo("ExtraBold", 84)
    y = 250
    for r in zalom(d, nazov, f_nadpis, 1040)[:2]:
        d.text((80, y), r, font=f_nadpis, fill=TEXT)
        y += 98
    f_pod = pismo("Regular", 36)
    y += 14
    for r in zalom(d, podtitul, f_pod, 1040)[:3]:
        d.text((80, y), r, font=f_pod, fill=SIVA)
        y += 48
    d.text((80, 560), "mestovcislach.sk · otvorené dáta so zdrojmi", font=pismo("SemiBold", 26), fill=CERVENA)
    return im


# nové podstránky každého mesta: public/og/<sekcia>-<mesto>.png (lokál „v Košiciach“ zo src/mesta.json)
SEKCIE_MIEST = {
    "volby": ("Komunálne voľby 2026 {v}", "Výsledky voľby primátora a mestského zastupiteľstva naživo, účasť a porovnanie s rokom 2022"),
    "kviz": ("Poznáš svoje mesto? {nazov}", "Kvíz z otvorených dát – 10 náhodných otázok o obyvateľoch, voľbách, doprave, bývaní a peniazoch mesta"),
    "zastupitelstvo": ("Mestské zastupiteľstvo {v}", "Kto sedí v zastupiteľstve, zloženie podľa strán a kto mandát obhájil"),
    "skoly": ("Školy {v}", "Všetky škôlky, základné a stredné školy – žiaci, učitelia, rozpočet a záujem o stredné školy"),
    "stvrte": ("Ktorá štvrť je pre mňa {v}", "Porovnajte štvrte podľa toho, čo potrebujete mať blízko – MHD, lekáreň, škola, škôlka"),
    "dane": ("Kam idú moje dane {v}", "Kalkulačka: koľko z vašich daní dostane mesto a na čo ich míňa"),
    "odchody": ("Odchody MHD {v}", "Kedy ide najbližšia električka, trolejbus či autobus – podľa cestovného poriadku, aj zo zastávok pri vás"),
    "pribeh": ("{nazov} za 10 rokov v číslach", "Obyvatelia, nové byty, ceny bytov, autá, školy a voľby – krátky príbeh na ťukanie"),
    "dosah": ("Kam sa dostanem MHD {v}", "Mapa: kam sa dostanete mestskou dopravou zo zastávky za 15, 30, 45 a 60 minút – aj s prestupmi"),
    "mestske-casti": ("Mestské časti {v}", "Obyvatelia, vek, voľby a dostupnosť služieb v každej mestskej časti"),
    "novinky": ("Čo je nové {v}", "Nové stavby, väčšie zmluvy mesta a zasadnutia zastupiteľstva – aj ako RSS"),
}


def kviz_obrazok(nazov: str, podtitul: str) -> Image.Image:
    """Tmavší variant pre kvíz (rovnaký štýl ako obrázok výsledku na zdieľanie)."""
    im = Image.new("RGB", (1200, 630), (19, 33, 63))
    d = ImageDraw.Draw(im)
    for x in range(1200):  # jemný prechod do vínovej
        k = x / 1200
        d.line([(x, 0), (x, 630)], fill=(int(19 + (91 - 19) * k), int(33 + (16 - 33) * k), int(63 + (34 - 63) * k)))
    d.text((80, 70), "?", font=pismo("Black", 150), fill=(255, 107, 128))
    f_nadpis = pismo("ExtraBold", 80)
    y = 250
    for r in zalom(d, nazov, f_nadpis, 1040)[:2]:
        d.text((80, y), r, font=f_nadpis, fill="white")
        y += 94
    y += 10
    for r in zalom(d, podtitul, pismo("Regular", 34), 1040)[:3]:
        d.text((80, y), r, font=pismo("Regular", 34), fill=(220, 224, 235))
        y += 46
    d.text((80, 560), "mestovcislach.sk · kvíz", font=pismo("SemiBold", 28), fill=(255, 140, 160))
    return im


# ---------- voľby 2026: obrázky s víťazom ----------
import re  # noqa: E402

SKRATKY = [
    (r"^Progresívne Slovensko$", "PS"), (r"^Sloboda a Solidarita$|^SaS$", "SaS"), (r"^Kresťanskodemokratické hnutie$|^KDH$", "KDH"),
    (r"^SMER - (sociálna demokracia|slovenská sociálna demokracia)$|^SMER-SD$", "Smer"), (r"^HLAS - sociálna demokracia$", "Hlas"),
    (r"^Slovenská národná strana$", "SNS"), (r"^Strana obcí a miest - SOM SLOVENSKO$", "SOM Slovensko"), (r"^OBYČAJNÍ ĽUDIA", "OĽaNO"),
    (r"^Občianska konzervatívna strana$", "OKS"), (r"^SME RODINA$", "Sme rodina"), (r"^ZA ĽUDÍ$", "Za ľudí"),
    (r"^DOBRÁ VOĽBA a Umiernení$", "Dobrá voľba"), (r"^SZÖVETSÉG", "Aliancia"), (r"^Hnutie Slovensko$", "Hnutie Slovensko"),
    (r"^Demokrati$", "Demokrati"), (r"^REPUBLIKA$", "Republika"), (r"^nezávislý kandidát$", "nezávislý kandidát"),
]


def skrat(strany: str) -> str:
    s = [next((k for r, k in SKRATKY if re.search(r, x.strip())), x.strip()) for x in (strany or "").split(", ") if x.strip()]
    return " + ".join(s[:3]) + (" a ďalší" if len(s) > 3 else "")


def bez_titulov(m: str) -> str:
    return " ".join(x for x in re.split(r"[\s,]+", m or "") if x and "." not in x and not re.fullmatch(r"PhD|MBA|LL|MPH|DiS|CSc|ArtD", x, re.I))


def vysledky_2026() -> dict[str, dict]:
    """slug → {primator: [...], ucast, priebezne, pct} pre mestá, kde už sú výsledky 2026."""
    import json
    koren = VYSTUP.parent.parent
    out = {}
    ba = koren / "data" / "komunalne-bratislava.json"
    if ba.exists():
        v = next((x for x in json.loads(ba.read_text(encoding="utf-8")).get("volby", []) if x.get("id") == "2026"), None)
        p = ((v or {}).get("oso") or {}).get("primator") or {}
        if p.get("kandidati"):
            sp = v.get("spracovanie") or {}
            out["bratislava"] = {"primator": p["kandidati"], "ucast": (p.get("ucast") or {}).get("ucast_pct"), "priebezne": bool(sp.get("priebezne")), "pct": sp.get("pct")}
    for m in json.loads((koren / "src" / "mesta.json").read_text(encoding="utf-8")):
        if not m.get("aktivne") or m["slug"] == "bratislava":
            continue
        f = koren / "data" / "mesta" / f"{m['slug']}.json"
        k = (json.loads(f.read_text(encoding="utf-8")).get("komunalne") or {}).get("2026") if f.exists() else None
        if k and k.get("primator"):
            sp = k.get("spracovanie") or {}
            out[m["slug"]] = {"primator": k["primator"], "ucast": (k.get("ucast") or {}).get("ucast_pct"), "priebezne": bool(sp.get("priebezne")), "pct": sp.get("pct")}
    return out


def volby_obrazok(nazov_mesta: str, v: dict) -> Image.Image:
    kand = sorted(v["primator"], key=lambda k: -(k.get("podiel") or 0))
    vitaz = next((k for k in kand if k.get("zvoleny")), kand[0])
    priebezne = v["priebezne"] or not any(k.get("zvoleny") for k in kand)
    im = Image.new("RGB", (1200, 630), (20, 22, 27))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1200, 12], fill=CERVENA)
    f = lambda r, s: pismo(r, s)  # noqa: E731
    d.text((80, 60), f"KOMUNÁLNE VOĽBY 2026 · {nazov_mesta.upper()}", font=f("Bold", 30), fill=(255, 140, 160))
    d.text((80, 112), "Priebežne vedie" if priebezne else "Zvolený primátor / zvolená primátorka", font=f("SemiBold", 40), fill=(220, 224, 235))
    meno = bez_titulov(vitaz["meno"])
    velkost = 84
    while d.textlength(meno, font=f("ExtraBold", velkost)) > 1040 and velkost > 50:
        velkost -= 4
    d.text((80, 168), meno, font=f("ExtraBold", velkost), fill="white")
    d.text((80, 168 + velkost + 18), skrat(vitaz.get("strany", ""))[:70], font=f("Regular", 32), fill=(200, 204, 214))
    # pruhy: prví traja kandidáti
    y = 360
    for k in kand[:3]:
        p = k.get("podiel") or 0
        d.text((80, y), bez_titulov(k["meno"])[:34], font=f("SemiBold", 28), fill="white")
        d.text((1120, y), f"{p:.1f} %".replace(".", ","), font=f("Bold", 28), fill="white", anchor="ra")
        d.rounded_rectangle([80, y + 40, 1120, y + 52], radius=6, fill=(55, 58, 66))
        d.rounded_rectangle([80, y + 40, 80 + max(12, int(1040 * p / 100)), y + 52], radius=6, fill=CERVENA if k is vitaz else (140, 146, 160))
        y += 66
    pozn = []
    if v.get("ucast") is not None:
        pozn.append(f"účasť {v['ucast']:.1f} %".replace(".", ","))
    if priebezne and v.get("pct") is not None:
        pozn.append(f"spracovaných {v['pct']:.0f} % okrskov")
    d.text((80, 570), " · ".join(pozn + ["mestovcislach.sk"]), font=f("SemiBold", 26), fill=(255, 140, 160))
    return im


def volby(len_zistit: bool = False) -> int:
    import json
    vys = vysledky_2026()
    if len_zistit:
        return 0 if vys else 1
    mesta = {m["slug"]: m["nazov"] for m in json.loads((VYSTUP.parent.parent / "src" / "mesta.json").read_text(encoding="utf-8"))}
    for slug, v in vys.items():
        volby_obrazok(mesta[slug], v).save(VYSTUP / f"volby-{slug}.png", optimize=True)
        print(f"volby-{slug}.png")
    return 0


def main() -> None:
    import json
    VYSTUP.mkdir(parents=True, exist_ok=True)
    for kluc, (nazov, podtitul) in STRANKY.items():
        obrazok(nazov, podtitul).save(VYSTUP / f"{kluc}.png", optimize=True)
        print(VYSTUP / f"{kluc}.png")
    mesta = [m for m in json.loads((VYSTUP.parent.parent / "src" / "mesta.json").read_text(encoding="utf-8")) if m.get("aktivne")]
    for m in mesta:
        for kluc, (nazov, podtitul) in SEKCIE_MIEST.items():
            if kluc in ("odchody", "dosah") and not (VYSTUP.parent.parent / "data" / kluc / f"{m['slug']}.json").exists():
                continue
            if kluc == "mestske-casti" and m["slug"] != "kosice":  # profily častí len pre Košice (BA má vlastné)
                continue
            n = nazov.format(nazov=m["nazov"], v=m["v"])
            (kviz_obrazok if kluc == "kviz" else obrazok)(n, podtitul).save(VYSTUP / f"{kluc}-{m['slug']}.png", optimize=True)
        print(f"{m['nazov']}: {len(SEKCIE_MIEST)} obrázkov")


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["volby"]:
        sys.exit(volby(len_zistit=sys.argv[2:3] == ["--treba"]))
    main()
