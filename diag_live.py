import re, requests
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
print(s.get("https://rozpocet.sk/web/init.js", timeout=60).text)
r = s.get("https://rozpocet.sk/web/", timeout=60)
print([x for x in re.findall(r'(?:src|href)="([^"]+)"', r.text) if "vendor" not in x])
for u in ["http://dataportal.nucem.sk/Dataportal-web/web/vysledky/2025/index.xhtml"]:
    r = s.get(u, timeout=60); print("==", u, r.status_code, len(r.text))
    print(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[:1500])
    for m in sorted(set(re.findall(r'href="([^"]+)"', r.text)))[:80]: print("  ", m[:200])
print("HOTOVO")
