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


def main() -> None:
    VYSTUP.mkdir(parents=True, exist_ok=True)
    for kluc, (nazov, podtitul) in STRANKY.items():
        obrazok(nazov, podtitul).save(VYSTUP / f"{kluc}.png", optimize=True)
        print(VYSTUP / f"{kluc}.png")


if __name__ == "__main__":
    main()
