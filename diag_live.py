import re, requests
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; mestovcislach.sk)"
B = "https://www.minv.sk/lnisdn/statistika/20260218_011722.691_2025-12-MS/statistika/"
r = s.get(B + "index-public.html", timeout=60); r.encoding = "utf-8"
al = re.findall(r"href='([^']+\.html)' title='([^']+)'", r.text)
c4 = [(h, t.replace("\n", " / ")) for h, t in al if re.search(r"-p?\d{4}\.html$", h)]
print("C4", len(c4)); print(c4[:4]); print(sorted({h.split('/')[1] for h, _ in c4}))
x = next(((h, t) for h, t in c4 if "dkvr" in h or ("od začiatku roka" in t and "všetky DN" in t)), None); print("PICK", x)
if x:
    y = s.get(B + x[0], timeout=60); y.encoding = "utf-8"
    print(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", y.text))[:1600])
print("HOTOVO")
