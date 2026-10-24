import requests, time
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
for i in range(40):
    if "foto-pas" in s.get("https://mestovcislach.sk/kosice/zivot/", timeout=30).text: break
    time.sleep(15)
for u in ("https://mestovcislach.sk/kosice/zivot/", "https://mestovcislach.sk/bratislava/doprava/", "https://mestovcislach.sk/trnava/samosprava/"):
    print(u, "pás:", "foto-pas" in s.get(u, timeout=30).text)
for u in ("https://mestovcislach.sk/img/mesta/kosice-zivot-800.webp", "https://mestovcislach.sk/img/mesta/bratislava-doprava-1600.webp"):
    r = s.get(u, timeout=30); print(u, r.status_code, r.headers.get("content-type"), len(r.content) // 1024, "kB")
print("HOTOVO")
