import requests, time
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
u = "https://mestovcislach.sk/vlozit/kosice/zivot?g=g-auta-a-cyklotrasy"
for i in range(40):
    r = s.get(u, timeout=30)
    if r.status_code == 200 and 'data-vlozit' in r.text: break
    time.sleep(15)
print(u, r.status_code, "| data-vlozit:", 'data-vlozit="g-auta-a-cyklotrasy"' in r.text, "| base:", '<base target="_top">' in r.text)
print("  X-Frame-Options:", r.headers.get("x-frame-options"), "| frame-ancestors:", [x.strip() for x in (r.headers.get("content-security-policy") or "").split(";") if "frame-ancestors" in x], "| robots:", r.headers.get("x-robots-tag"))
r2 = s.get("https://mestovcislach.sk/kosice/zivot/", timeout=30); print("bežná stránka X-Frame-Options:", r2.headers.get("x-frame-options"))
for u in ("https://mestovcislach.sk/vlozit/api/asistent?g=x", "https://mestovcislach.sk/vlozit/neexistuje?g=x", "https://mestovcislach.sk/kosice/adresa/", "https://mestovcislach.sk/data/mesta/adresa/kosice.json", "https://mestovcislach.sk/bratislava/adresa/"):
    r = s.get(u, timeout=30); print(u, r.status_code)
r = s.get("https://nominatim.openstreetmap.org/search", params={"q": "Hlavná 10, Košice", "format": "jsonv2", "countrycodes": "sk", "limit": 1}, timeout=30, headers={"Referer": "https://mestovcislach.sk/"})
print("Nominatim:", r.status_code, r.headers.get("access-control-allow-origin"), len(r.json()) if r.ok else r.text[:100])
