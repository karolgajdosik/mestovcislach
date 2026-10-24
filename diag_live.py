# Ďalšie fotky miest z Wikimedia Commons (voľné licencie) – kandidáti s náhľadmi.
import requests, json, os, re, html
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach; info@mestovcislach.sk)"
API = "https://commons.wikimedia.org/w/api.php"
DOTAZY = {
 "bratislava-radnica": ["Primate's Palace Bratislava", "Primaciálny palác Bratislava", "Old Town Hall Bratislava"],
 "kosice-radnica": ["Košice historická radnica", "Kosice town hall Hlavna"],
 "presov-radnica": ["Prešov radnica Hlavná", "Presov town hall"],
 "zilina-radnica": ["Žilina radnica Námestie obetí komunizmu", "Zilina town hall"],
 "banska-bystrica-radnica": ["Banská Bystrica radnica", "Banska Bystrica town hall Pretorium"],
 "nitra-radnica": ["Nitra radnica Štefánikova", "Nitra town hall"],
 "trnava-radnica": ["Trnava radnica Hlavná", "Trnava town hall"],
 "trencin-radnica": ["Trenčín mestský úrad Mierové námestie", "Trencin Mierove namestie"],
 "kosice-zivot": ["Košice Mestský park", "Kosice Hlavna fountain"],
 "presov-zivot": ["Prešov Hlavná ulica fontána", "Presov park"],
 "zilina-zivot": ["Žilina Národná ulica", "Zilina Hlinkovo namestie"],
 "banska-bystrica-zivot": ["Banská Bystrica Mestský park", "Banska Bystrica Hron"],
 "nitra-zivot": ["Nitra Svätoplukovo námestie", "Nitra pedestrian zone Štefánikova"],
 "trnava-zivot": ["Trnava Hlavná ulica", "Trnava pedestrian street"],
 "trencin-zivot": ["Trenčín Mierové námestie", "Trencin Vah river"],
 "bratislava-doprava": ["Bratislava tram", "Bratislava trolleybus", "Bratislava Škoda 30T"],
 "bratislava-vystavba": ["Bratislava skyline new buildings", "Bratislava Eurovea Tower", "Bratislava Nivy Tower"],
 "bratislava-prostredie": ["Sad Janka Kráľa Bratislava", "Danube Bratislava embankment park", "Bratislava Horský park"],
 "bratislava-obyvatelia": ["Petržalka housing estate", "Bratislava Petržalka panorama"],
}
POVOLENE = re.compile(r"^(CC0|CC BY(-SA)? [1-4]\.0|CC BY(-SA)? 2\.5|Public domain|PD)", re.I)
os.makedirs("diag/foto", exist_ok=True)
vystup = {}
for kluc, dotazy in DOTAZY.items():
    videne, kand = set(), []
    for q in dotazy:
        try:
            d = s.get(API, params={"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{q} filetype:bitmap",
                                   "gsrlimit": 25, "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 400}, timeout=60).json()
        except Exception as e:
            print(kluc, q, e); continue
        for p in sorted((d.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99)):
            ii = (p.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata", {})
            lic = em.get("LicenseShortName", {}).get("value", "")
            w, h = ii.get("width", 0), ii.get("height", 0)
            if p["title"] in videne or not POVOLENE.match(lic) or w < 2000 or not h or w / h < 1.3 or w / h > 3 or ii.get("mime") != "image/jpeg": continue
            videne.add(p["title"])
            kand.append({"title": p["title"], "lic": lic, "w": w, "h": h, "thumb": ii.get("thumburl")})
            if len(kand) >= 6: break
        if len(kand) >= 6: break
    for i, k in enumerate(kand):
        open(f"diag/foto/{kluc}-{i}.jpg", "wb").write(s.get(k["thumb"], timeout=60).content)
    vystup[kluc] = kand
    print(kluc, len(kand))
json.dump(vystup, open("diag/foto/kandidati3.json", "w"), ensure_ascii=False, indent=1)
print("HOTOVO")
