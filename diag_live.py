import time, urllib.request
UA={"User-Agent":"mestovcislach.sk diag"}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u+("&" if "?" in u else "?")+"v=%d"%time.time(),headers=UA),timeout=30); return r.status, r.read().decode()
    except Exception as e: return getattr(e,"code",0), ""
for i in range(30):
    s,h=get("https://mestovcislach.sk/zilina/kviz")
    if s==200 and "kv-start" in h: break
    time.sleep(20)
for u in ["/zilina/stvrte","/bratislava/stvrte","/kosice/skoly","/trencin/zastupitelstvo","/bratislava/dane","/presov/novinky","/presov/novinky.xml","/nitra/kviz","/data/hladanie.json"]:
    s,h=get("https://mestovcislach.sk"+u); print(u, s, len(h))
print("HOTOVO")
