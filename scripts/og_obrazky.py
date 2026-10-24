"""Náhľadové obrázky (Open Graph, 1200 × 630) pre zdieľanie stránok na sociálnych sieťach a v aplikáciách.

Spúšťa sa ručne pri zmene stránok: python scripts/og_obrazky.py → public/og/<stránka>.png
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


def main() -> None:
    import json
    VYSTUP.mkdir(parents=True, exist_ok=True)
    for kluc, (nazov, podtitul) in STRANKY.items():
        obrazok(nazov, podtitul).save(VYSTUP / f"{kluc}.png", optimize=True)
        print(VYSTUP / f"{kluc}.png")
    mesta = [m for m in json.loads((VYSTUP.parent.parent / "src" / "mesta.json").read_text(encoding="utf-8")) if m.get("aktivne")]
    for m in mesta:
        for kluc, (nazov, podtitul) in SEKCIE_MIEST.items():
            if kluc == "odchody" and not (VYSTUP.parent.parent / "data" / "odchody" / f"{m['slug']}.json").exists():
                continue
            if kluc == "mestske-casti" and m["slug"] != "kosice":  # profily častí len pre Košice (BA má vlastné)
                continue
            n = nazov.format(nazov=m["nazov"], v=m["v"])
            (kviz_obrazok if kluc == "kviz" else obrazok)(n, podtitul).save(VYSTUP / f"{kluc}-{m['slug']}.png", optimize=True)
        print(f"{m['nazov']}: {len(SEKCIE_MIEST)} obrázkov")


if __name__ == "__main__":
    main()
