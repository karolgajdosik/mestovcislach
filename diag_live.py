import requests, re, time
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
r = s.get("https://volby.statistics.sk/", timeout=30); print("volby.statistics.sk:", repr(r.text[:200]))
for u in ("https://data.statistics.sk/api/v2/collection?lang=sk", "https://slovak.statistics.sk/"):
    try: r = s.get(u, timeout=40); print(u, r.status_code, len(r.content))
    except Exception as e: print(u, type(e).__name__)
# živý web vs. repozitár: dátum zmeny prehľadu Žiliny (data/mesta/zilina.json -> /data/mesta/zilina.json)
r = s.get("https://mestovcislach.sk/data/mesta/zilina.json", timeout=30); print("živý /data/mesta/zilina.json:", r.status_code, r.json().get("aktualizovane") if r.ok else "")
for u in ("https://mestovcislach.sk/", "https://mestovcislach.sk/bratislava/", "https://mestovcislach.sk/kosice/", "https://mestovcislach.sk/bratislava/volby/", "https://mestovcislach.sk/sitemap.xml"):
    t0 = time.time(); r = s.get(u, timeout=30); print(u, r.status_code, f"{(time.time()-t0)*1000:.0f} ms", len(r.content)//1024, "kB")
r = s.post("https://mestovcislach.sk/api/asistent", json={"otazka": "Koľko obyvateľov má Žilina?", "mesto": "zilina"}, timeout=60); print("asistent:", r.status_code, r.text[:200].replace("\n", " "))
