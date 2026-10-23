# Kandidáti fotiek miest z Wikimedia Commons (voľné licencie) – náhľady + metadáta (autor, licencia).
import requests, json, os, re, html
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach; info@mestovcislach.sk)"
API = "https://commons.wikimedia.org/w/api.php"
DOTAZY = {
 "bratislava": ["Bratislava castle panorama Danube", "Bratislava old town skyline"],
 "kosice": ["Košice Hlavná ulica cathedral", "Kosice St. Elisabeth Cathedral square"],
 "presov": ["Prešov Hlavná ulica", "Presov main square"],
 "zilina": ["Žilina Mariánske námestie", "Zilina square"],
 "banska-bystrica": ["Banská Bystrica námestie SNP", "Banska Bystrica square"],
 "nitra": ["Nitra castle panorama", "Nitra hrad Zobor"],
 "trnava": ["Trnava panorama", "Trnava Trojičné námestie"],
 "trencin": ["Trenčín castle town", "Trencin hrad panorama"],
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
            if len(kand) >= 6: break
        if len(kand) >= 6: break
    for i, k in enumerate(kand):
        open(f"diag/foto/{mesto}-{i}.jpg", "wb").write(s.get(k["thumb"], timeout=60).content)
    vystup[mesto] = kand
    print(mesto, len(kand), [(k["title"][5:60], k["lic"], f"{k['w']}x{k['h']}") for k in kand])
json.dump(vystup, open("diag/foto/kandidati.json", "w"), ensure_ascii=False, indent=1)
print("HOTOVO")
