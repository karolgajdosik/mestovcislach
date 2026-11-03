import re, urllib.request
for u in ["https://mestovcislach.sk/banskobystricky-kraj/banska-bystrica/badin/", "https://mestovcislach.sk/kosice/", "https://mestovcislach.sk/bratislava/"]:
    h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()
    i = h.find('id="kalendar"')
    print(u, i >= 0, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h[i:i+1500]))[:300] if i >= 0 else "")
print("HOTOVO")
