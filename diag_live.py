import requests, time, re
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
def js(u):
    t = s.get(u, timeout=30).text
    return [x for x in re.findall(r'src="(/_astro/[^"]+\.js)"', t)]
for pokus in range(30):
    if any("World_Imagery" in s.get("https://mestovcislach.sk" + j, timeout=30).text for j in js("https://mestovcislach.sk/zilina/mapa/")): break
    time.sleep(15)
for m in ("zilina", "kosice", "nitra"):
    print(m, "satelitná snímka v skripte mapy:", any("World_Imagery" in s.get("https://mestovcislach.sk" + j, timeout=30).text for j in js(f"https://mestovcislach.sk/{m}/mapa/")))
r = s.get("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/14/5640/9100", timeout=30); print("dlaždica Esri:", r.status_code, r.headers.get("content-type"))
