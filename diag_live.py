import re, requests
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
for j in ["common/services.js", "app/services.js"]:
    t = s.get("https://rozpocet.sk/web/" + j, timeout=60).text
    print("JS", j, len(t))
    for m in sorted(set(re.findall(r'["\']([^"\'\s]*(?:/api|rest|ws|json|\.php|/data)[^"\'\s]*)["\']', t)))[:80]: print("   ", m)
u = "http://dataportal.nucem.sk/Dataportal-web/web/vysledky/2025/testovanie/index.xhtml"
r = s.get(u, timeout=60); print("==", u, r.status_code, len(r.text))
print(re.sub(r"\s+", " ", re.sub(r"<script.*?</script>", " ", r.text, flags=re.S))[:4000])
print("HOTOVO")
