import re, requests
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
t = s.get("https://rozpocet.sk/web/app/services.js", timeout=60).text
for m in sorted(set(re.findall(r"""['"]([a-zA-Z0-9_\-/]+(?:/[a-zA-Z0-9_\-{}]+){1,})['"]""", t)))[:120]: print("  P", m)
i = t.find("rest/api"); print(t[max(0,i-600):i+400])
u = "http://dataportal.nucem.sk/Dataportal-web/web/vysledky/2025/testovanie/index.xhtml"
r = s.get(u, timeout=60)
h = re.sub(r"<script.*?</script>", " ", r.text, flags=re.S)
for m in re.findall(r'<select id="([^"]+)"[^>]*>(.*?)</select>', h, flags=re.S):
    print("SELECT", m[0], re.findall(r'value="([^"]*)">([^<]*)', m[1])[:12])
print(re.findall(r'(?:button|input)[^>]*(?:id|name|value)="([^"]+)"', h)[:40])
print(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))[-1500:])
print("HOTOVO")
