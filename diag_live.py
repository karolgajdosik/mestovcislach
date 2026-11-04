import re, urllib.request
for u in ["https://mestovcislach.sk/kosicky-kraj/sobrance/sejkov/", "https://mestovcislach.sk/kosicky-kraj/michalovce/senne/"]:
    try:
        h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()
    except Exception as e:
        print(u, e); continue
    i = h.find('id="hospodarenie"')
    print(u, "sekcia:", i >= 0, "zmluvy:", "id=\"zmluvy\"" in h, re.search(r"<title>(.*?)<", h).group(1) if "<title>" in h else "")
    if i >= 0:
        t = re.sub(r"<[^>]+>", " ", h[i:i+6000]); print(re.sub(r"\s+", " ", t)[:900])
print("HOTOVO")
