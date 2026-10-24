import requests, json, re, html, os
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach; info@mestovcislach.sk)"
VYBER = {"bratislava-radnica": "File:Primate's Palace in Bratislava.jpg", "kosice-radnica": "File:Košice - Hlavná 59 -b.jpg", "presov-radnica": "File:Leto, Hlavná ulica, radnica. Prešov 22 Slovakia.jpg", "zilina-radnica": "File:Žilina, Radnice.jpg", "banska-bystrica-radnica": "File:Banská Bystrica - Barbakán - Mestský hrad v Banskej Bystrici 005.jpg", "nitra-radnica": "File:Topoľčany mestský úrad 1.jpg", "trnava-radnica": "File:Slovakia - Trnava - Radnica RB01.jpg", "trencin-radnica": "File:Mestský úrad Trenčín a Dolná brána.jpg", "kosice-zivot": "File:Plávajúca fontána, Mestský park, Košice, 2026.jpg", "presov-zivot": "File:Adventný veniec. Prešov 23 Slovakia.jpg", "zilina-zivot": "File:Národná street in Žilina.jpg", "banska-bystrica-zivot": "File:Banská Bystrica - Mestský park (2).jpg", "nitra-zivot": "File:Nitra - Svätoplukovo námestie (1).jpg", "trnava-zivot": "File:Trnava Hlavná 05 03.jpg", "trencin-zivot": "File:Trenčín, Mierové námestie a hrad (1).jpg", "bratislava-doprava": "File:Bratislava Tram R05.jpg", "bratislava-vystavba": "File:Eurovea Tower vo výstavbe 2.jpg", "bratislava-prostredie": "File:Sad Janka Kráľa - view of Bratislava Castle and the Old Town.jpg", "bratislava-obyvatelia": "File:Danube Bratislava 6.jpg"}
os.makedirs("diag/foto", exist_ok=True)
kredity = {}
for m, k in VYBER.items():
    d = s.get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "format": "json", "titles": k, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 2000}, timeout=60).json()
    ii = next(iter(d["query"]["pages"].values()))["imageinfo"][0]; em = ii["extmetadata"]
    autor = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(em.get("Artist", {}).get("value", "")))).strip()
    kredity[m] = {"subor": k, "autor": autor, "licencia": em.get("LicenseShortName", {}).get("value"), "licencia_url": em.get("LicenseUrl", {}).get("value"), "zdroj": ii["descriptionurl"]}
    open(f"diag/foto/full-{m}.jpg", "wb").write(s.get(ii["thumburl"], timeout=120).content)
    print(m, kredity[m]["licencia"], os.path.getsize(f"diag/foto/full-{m}.jpg") // 1024, "kB")
json.dump(kredity, open("diag/foto/kredity3.json", "w"), ensure_ascii=False, indent=1)
print("HOTOVO")
