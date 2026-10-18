import requests, time
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
for pokus in range(20):
    if 'class="mesta-pas"' in s.get("https://mestovcislach.sk/kosice/", timeout=30).text: break
    time.sleep(15)
for u in ("https://mestovcislach.sk/kosice/", "https://mestovcislach.sk/bratislava/", "https://mestovcislach.sk/", "https://mestovcislach.sk/kosice/mapa/"):
    t = s.get(u, timeout=30).text
    print(u, "mesta-pas:", 'class="mesta-pas"' in t, "| bočné menu:", 'class="bocne"' in t, "| úzke:", " uzke" in t)
