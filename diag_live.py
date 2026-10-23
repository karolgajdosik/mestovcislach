# Kandidáti fotiek miest z Wikimedia Commons (voľné licencie) – náhľady + metadáta (autor, licencia).
import requests, json, os, re, html
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach; info@mestovcislach.sk)"
API = "https://commons.wikimedia.org/w/api.php"
DOTAZY = {
 "nitra": ["Nitra castle", "Nitriansky hrad", "Nitra Svätoplukovo námestie", "Nitra Pribinovo námestie", "Nitra panorama Zobor", "Nitra Slovakia"],
 "presov": ["Prešov Konkatedrála sv. Mikuláša", "Presov cathedral Hlavna", "Prešov panorama", "Prešov Slovakia old town"],
}
POVOLENE = re.compile(r"^(CC0|CC BY(-SA)? [1-4]\.0|CC BY(-SA)? 2\.5|Public domain|PD)", re.I)
os.makedirs("diag/foto", exist_ok=True)
vystup = {}
for mesto, dotazy in DOTAZY.items():
    videne, kand = set(), []
    for q in dotazy:
        d = s.get(API, params={"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{q} filetype:bitmap",
                               "gsrlimit": 20, "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 480}, timeout=60).json()
        for p in sorted((d.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99)):
            ii = (p.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata", {})
            lic = em.get("LicenseShortName", {}).get("value", "")
            w, h = ii.get("width", 0), ii.get("height", 0)
            if p["title"] in videne or not POVOLENE.match(lic) or w < 2000 or not h or w / h < 1.35 or w / h > 2.6 or ii.get("mime") != "image/jpeg": continue
            videne.add(p["title"])
            autor = re.sub(r"<[^>]+>", "", html.unescape(em.get("Artist", {}).get("value", ""))).strip()
            kand.append({"title": p["title"], "lic": lic, "autor": autor[:80], "w": w, "h": h, "thumb": ii.get("thumburl"), "url": ii.get("url"), "page": ii.get("descriptionurl")})
            if len(kand) >= 9: break
        if len(kand) >= 9: break
    for i, k in enumerate(kand):
        open(f"diag/foto/{mesto}-b{i}.jpg", "wb").write(s.get(k["thumb"], timeout=60).content)
    vystup[mesto] = kand
    print(mesto, len(kand), [(k["title"][5:60], k["lic"], f"{k['w']}x{k['h']}") for k in kand])
json.dump(vystup, open("diag/foto/kandidati2.json", "w"), ensure_ascii=False, indent=1)
print("HOTOVO")
