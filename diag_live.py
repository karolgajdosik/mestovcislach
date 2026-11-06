import re, requests, json
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk (info@mestovcislach.sk)"
u = "http://dataportal.nucem.sk/Dataportal-web/web/vysledky/2025/testovanie/index.xhtml"
h = s.get(u, timeout=60).text
for m in re.finditer(r'<a[^>]*href="#"[^>]*>', h): print("LINK", m.group(0)[:500])
for m in re.finditer(r'<form[^>]*>', h): print("FORM", m.group(0)[:300])
print("VS", re.findall(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h)[:2])
t = s.get("https://rozpocet.sk/web/app/services.js", timeout=60).text
for k in ["rozpocetSamOrg/", "rozpoctySamOrg/", "organizacie/podurovne/", "organizacie/info/", "polozkySumarPodurovni", "organizacie/po/"]:
    i = t.find(k); print("==", k, t[max(0, i-300):i+300].replace("\n", " "))
c = s.get("https://rozpocet.sk/web/app/app.js", timeout=60).text
print("ROUTES", re.findall(r'when\("([^"]+)"', c)[:60])
print("HOTOVO")
