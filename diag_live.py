import requests, json, re, html, os
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach; info@mestovcislach.sk)"
VYBER = {"bratislava": "File:Bratislava Panorama R01.jpg", "kosice": "File:Main Street, Košice, Slovakia 1.jpg", "zilina": "File:Mariánské námestie, Žilina, okres Žilina, Žilinský kraj, Slovensko 02.jpg", "banska-bystrica": "File:Banská Bystrica - Námestie SNP 004.jpg", "trnava": "File:Square of the Holy Trinity (Trojičné námestie), Trnava, Slovakia.JPG", "trencin": "File:Trenčín Castle 58.jpg", "nitra": "File:Nitriansky hrad.jpg", "presov": "File:Panorama, Prešov 22 Slovakia 6.jpg"}
kredity = {}
for m, k in VYBER.items():
    d = s.get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "format": "json", "titles": k, "prop": "imageinfo",
              "iiprop": "url|extmetadata", "iiurlwidth": 2000}, timeout=60).json()
    ii = next(iter(d["query"]["pages"].values()))["imageinfo"][0]; em = ii["extmetadata"]
    autor = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(em.get("Artist", {}).get("value", "")))).strip()
    kredity[m] = {"subor": k, "autor": autor, "licencia": em.get("LicenseShortName", {}).get("value"), "licencia_url": em.get("LicenseUrl", {}).get("value"), "zdroj": ii["descriptionurl"]}
    open(f"diag/foto/full-{m}.jpg", "wb").write(s.get(ii["thumburl"], timeout=120).content)
    print(m, kredity[m]["licencia"], "|", kredity[m]["autor"][:60], "|", os.path.getsize(f"diag/foto/full-{m}.jpg") // 1024, "kB")
json.dump(kredity, open("diag/foto/kredity.json", "w"), ensure_ascii=False, indent=1)
print("HOTOVO")
