import requests
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
for u in ["https://mestovcislach.sk/presov/zastupitelstvo", "https://mestovcislach.sk/presov/zastupitelstvo/", "https://mestovcislach.sk/dodavatelia",
          "https://mestovcislach.sk/katalog/ed15579d1a65471187497a534b8de8f4", "https://mestovcislach.sk/porovnaj/?a=kosice", "https://mestovcislach.sk/porovnaj?a=kosice",
          "https://mestovcislach.sk/kosice/mestske-casti/dzungla", "https://mestovcislach.sk/kosice/mestske-casti/dzungla/"]:
    r = s.get(u, allow_redirects=False, timeout=30)
    print(r.status_code, u, "->", r.headers.get("location"))
h = s.get("https://mestovcislach.sk/porovnaj/?a=kosice", timeout=30).text
import re
print("canonical", re.findall(r'<link rel="canonical"[^>]*>', h)[:2], re.findall(r'http-equiv="refresh"[^>]*>', h)[:1])
print("HOTOVO")
