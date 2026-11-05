import re, json, requests
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36", "Accept": "application/json"}
B = "https://statdata.statistics.sk/public/api/dc"
for u, kw in [(B + "/public/bulkDownload/search", {}), (B + "/public/bulkDownload/search?query=odpad", {}), (B + "/public/recentlyUpdated", {})]:
    for m in ("get", "post"):
        try:
            r = getattr(requests, m)(u, headers=H, timeout=90, **({"json": {"query": "odpad", "page": 0, "size": 100}} if m == "post" else {}))
        except Exception as e:
            print(u, m, e); continue
        print(u, m, r.status_code, len(r.text))
        if r.ok:
            t = r.text
            print(t[:400])
            for x in re.finditer(r"odpad", t, re.I):
                print("   ...", t[max(0, x.start()-200):x.start()+120].replace("\n", " "))
# sekcie – vypíš celý strom názvov sekcií a hľadaj "Životné"
r = requests.get(B + "/public/sections/expandAll", headers=H, timeout=120)
def walk(n, d=0):
    for c in n:
        nm = (c.get("nameSk") or "").strip()
        if d < 2 or re.search(r"život|odpad|trh práce|škol|vzdel", nm, re.I): print("  " * d + nm, c.get("id"))
        walk(c.get("children") or [], d + 1)
walk(r.json())
print("HOTOVO")
