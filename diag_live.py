import re, requests
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
r = s.get("https://rozpocet.sk/web/", timeout=60)
js = [j for j in re.findall(r'src="([^"]+\.js)"', r.text) if "vendor" not in j]
print("appjs", js)
for j in js:
    t = s.get("https://rozpocet.sk/web/" + j.lstrip("/"), timeout=60).text
    urls = sorted(set(re.findall(r'["\']((?:https?://[^"\']+|/[a-zA-Z0-9_\-]+/[^"\']*)(?:api|rest|service|data)[^"\']*)["\']', t)))
    print("JS", j, len(t), urls[:40])
    for m in sorted(set(re.findall(r'["\']([^"\']*(?:api|rest)/[^"\']{2,80})["\']', t)))[:60]: print("   ", m)
for u in ["https://vysledky.nucem.sk/", "https://vysledky.nucem.sk/t9/", "https://www2.nucem.sk/sk/merania/narodne-merania/testovanie-9"]:
    try:
        r = s.get(u, timeout=60); print("==", u, r.status_code)
        for m in sorted(set(re.findall(r'href="([^"]+)"', r.text))):
            if re.search(r"t9|testovan|vysled|skol|xls|csv|zip", m, re.I): print("  ", m[:200])
    except Exception as e: print("ERR", u, e)
print("HOTOVO")
