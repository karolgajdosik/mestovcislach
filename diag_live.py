import re, urllib.request, time
time.sleep(420)
for u in ["https://mestovcislach.sk/banskobystricky-kraj/rimavska-sobota/tisovec/", "https://mestovcislach.sk/kosicky-kraj/sobrance/sejkov/"]:
    h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()
    print(u, {i: f'id="{i}"' in h for i in ("nezamestnanost", "eurofondy", "skoly", "odpad", "kalendar", "pocasie")})
    for i in ("nezamestnanost", "eurofondy"):
        j = h.find(f'id="{i}"')
        if j > 0: print("  ", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h[j:j+1500]))[:260])
print("HOTOVO")
