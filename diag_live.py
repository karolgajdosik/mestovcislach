import requests, zipfile, io, csv
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk diag"
it = "f1033ca6c2f4461d9aba285e1c7cb079"
try:
    m = s.get(f"https://www.arcgis.com/sharing/rest/content/items/{it}", params={"f": "json"}, timeout=60).json()
    print("položka:", m.get("title"), m.get("type"), m.get("owner"), m.get("modified"), m.get("licenseInfo", "")[:200], m.get("size"), m.get("url"))
except Exception as e: print("meta", e)
for u in (f"https://www.arcgis.com/sharing/rest/content/items/{it}/data", "https://gtfs.sk/", "https://www.dpmp.sk/"):
    try:
        r = s.get(u, timeout=120); print(u, r.status_code, r.headers.get("content-type"), len(r.content), r.content[:2])
        if r.content[:2] == b"PK":
            z = zipfile.ZipFile(io.BytesIO(r.content)); print("  súbory:", [(n, z.getinfo(n).file_size) for n in z.namelist()])
            for n in ("agency.txt", "feed_info.txt", "calendar.txt"):
                if n in z.namelist():
                    rows = list(csv.DictReader(io.StringIO(z.read(n).decode("utf-8-sig"))))
                    print(" ", n, len(rows), rows[:2])
            for n in ("routes.txt", "stops.txt", "trips.txt"):
                if n in z.namelist(): print(" ", n, len(z.read(n).decode("utf-8-sig").splitlines()) - 1, "riadkov")
            if "calendar_dates.txt" in z.namelist():
                d = list(csv.DictReader(io.StringIO(z.read("calendar_dates.txt").decode("utf-8-sig")))); print("  calendar_dates", len(d), min(x["date"] for x in d), max(x["date"] for x in d))
        elif "html" in (r.headers.get("content-type") or ""):
            import re; print("  odkazy:", sorted(set(h for h in re.findall(r'href="([^"]+)"', r.text) if "gtfs" in h.lower() or "zip" in h.lower()))[:30])
    except Exception as e: print(u, type(e).__name__, e)
print("HOTOVO")
