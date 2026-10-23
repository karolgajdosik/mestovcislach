import requests, json, re, html, os
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (github.com/karolgajdosik/mestovcislach; info@mestovcislach.sk)"
k1 = json.load(open("diag/foto/kandidati.json")); k2 = json.load(open("diag/foto/kandidati2.json"))
VYBER = {"bratislava": k1["bratislava"][0], "kosice": k1["kosice"][3], "zilina": k1["zilina"][5], "banska-bystrica": k1["banska-bystrica"][0],
         "trnava": k1["trnava"][3], "trencin": k1["trencin"][0], "nitra": k2["nitra"][4], "presov": k2["presov"][5]}
kredity = {}
for m, k in VYBER.items():
    d = s.get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "format": "json", "titles": k["title"], "prop": "imageinfo",
              "iiprop": "url|extmetadata", "iiurlwidth": 2000}, timeout=60).json()
    ii = next(iter(d["query"]["pages"].values()))["imageinfo"][0]; em = ii["extmetadata"]
    autor = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(em.get("Artist", {}).get("value", "")))).strip()
    kredity[m] = {"subor": k["title"], "autor": autor, "licencia": em.get("LicenseShortName", {}).get("value"), "licencia_url": em.get("LicenseUrl", {}).get("value"), "zdroj": ii["descriptionurl"]}
    open(f"diag/foto/full-{m}.jpg", "wb").write(s.get(ii["thumburl"], timeout=120).content)
    print(m, kredity[m]["licencia"], "|", kredity[m]["autor"][:60], "|", os.path.getsize(f"diag/foto/full-{m}.jpg") // 1024, "kB")
json.dump(kredity, open("diag/foto/kredity.json", "w"), ensure_ascii=False, indent=1)
print("HOTOVO")
