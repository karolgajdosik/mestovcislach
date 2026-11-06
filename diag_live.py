import re, requests, json
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
u = "http://dataportal.nucem.sk/Dataportal-web/web/vysledky/2025/testovanie/index.xhtml"
h = s.get(u, timeout=60).text
for m in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]*)', h):
    if re.search(r"xls|csv|zip|pdf|stiah|dl/|Matematika", m[0] + m[1], re.I): print("A", m)
# rozpocet API
t = s.get("https://rozpocet.sk/web/app/services.js", timeout=60).text
for fn in re.findall(r'l\("([^"]+)"', t)[:80]: print("  L", fn)
for p in ["rozpocet/SAM/sam/0", "rozpocet/sumareZaRoky", "rozpocet/poslednaAktualizacia/SAM/SAM/SCH"]:
    try:
        r = s.get("https://rozpocet.sk/rest/api/" + p, timeout=60)
        print("API", p, r.status_code, r.headers.get("content-type"), r.text[:800].replace("\n", " "))
    except Exception as e: print("ERR", p, e)
print("HOTOVO")
