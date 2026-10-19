import requests, re
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
for m in ("zilina", "kosice"):
    t = s.get(f"https://mestovcislach.sk/{m}/mapa/", timeout=30).text
    hl = [x for x in re.findall(r'src="(/_astro/mapa[^"]+\.js)"', t)]
    kod = s.get("https://mestovcislach.sk" + hl[0], timeout=30).text
    chunky = re.findall(r'from"\./([^"]+)"', kod)
    print(m, hl, any("World_Imagery" in s.get("https://mestovcislach.sk/_astro/" + c, timeout=30).text for c in chunky))
