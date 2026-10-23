import requests, time
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
for i in range(40):
    if "odber-form" in s.get("https://mestovcislach.sk/kosice/upozornenia/", timeout=30).text: break
    time.sleep(15)
for u in ("https://mestovcislach.sk/kosice/upozornenia/", "https://mestovcislach.sk/bratislava/upozornenia/", "https://mestovcislach.sk/odber-potvrdeny/"):
    t = s.get(u, timeout=30).text; print(u, "formulár:", "odber-form" in t)
r = s.post("https://mestovcislach.sk/api/odber", json={"email": "neplatna-adresa", "kanal": "kosice", "suhlas": True}, timeout=30)
print("neplatná adresa:", r.status_code, r.json())
r = s.post("https://mestovcislach.sk/api/odber", json={"email": "x@example.com", "kanal": "neexistuje", "suhlas": True}, timeout=30)
print("neznámy kanál:", r.status_code, r.json())
print("HOTOVO")
