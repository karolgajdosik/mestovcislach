import re, json, requests
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
for u in ["https://www.upsvr.gov.sk/statistiky/mesacne-statistiky-miest-a-obci.html?page_id=1009850", "https://www.upsvr.gov.sk/statistiky/mesacne-statistiky-miest-a-obci/2020.html?page_id=1009851"]:
    r = requests.get(u, headers=H, timeout=60)
    i = r.text.find('id="content"'); i = i if i > 0 else r.text.find("<h1")
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", r.text[i:i+8000]))
    print(u, "\n", txt[:1500])
    print([x for x in re.findall(r'href="([^"]+)"', r.text) if "docs" in x and not x.endswith((".css", ".js"))][:30])
r = requests.get("https://statdata.statistics.sk/public/api/dc/public/sections/expandAll", headers=H, timeout=120)
t = r.text
print(t[:800])
for m in re.finditer(r"odpad|Odpad", t):
    print("  ", t[max(0, m.start()-250):m.start()+150].replace("\n", " "))
print("HOTOVO")
