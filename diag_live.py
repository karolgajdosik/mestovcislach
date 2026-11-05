import re, requests
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
seen = set()
def links(u):
    r = requests.get(u, headers=H, timeout=60)
    print(u, r.status_code, len(r.text))
    out = []
    for h, t in re.findall(r'href="([^"#]+)"[^>]*>(.*?)</a>', r.text, re.S):
        t = re.sub(r"<[^>]+>|\s+", " ", t).strip()
        if h.startswith("/"): h = "https://www.isoh.gov.sk" + h
        out.append((h, t))
    return out
for u in ["https://www.isoh.gov.sk/", "https://www.isoh.gov.sk/verejne-vystupy"]:
    try:
        for h, t in links(u):
            if "isoh.gov.sk" in h and h not in seen and re.search(r"výstup|vystup|štatist|statist|obc|komun|vytried|report|dáta|data|xls|csv", h + t, re.I):
                seen.add(h); print("  ", t[:80], "|", h)
    except Exception as e:
        print("ERR", u, e)
print("HOTOVO")
