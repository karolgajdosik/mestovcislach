# Živý web: robots.txt, sitemap.xml, JSON-LD (len počty a hlavičky).
import re, requests
s = requests.Session(); s.headers["User-Agent"] = "mestovcislach.sk diag"
r = s.get("https://mestovcislach.sk/robots.txt", timeout=30); print("robots", r.status_code, r.headers.get("content-type"), r.text.strip().splitlines()[-1])
r = s.get("https://mestovcislach.sk/sitemap.xml", timeout=30); print("sitemap", r.status_code, r.headers.get("content-type"), r.text.count("<url>"))
r = s.get("https://mestovcislach.sk/", timeout=30); print("úvod ld+json", r.text.count("application/ld+json"), "| canonical", re.findall(r'rel="canonical" href="([^"]+)"', r.text))
r = s.get("https://mestovcislach.sk/bratislava/katalog/970eb74db22b488c8175df085641c822/", timeout=30); print("dataset", r.status_code, r.text.count('"@type":"Dataset"'))
for u in ("https://mestovcislach.sk/bratislava/doprava", "http://mestovcislach.sk/", "https://www.mestovcislach.sk/", "https://mestovcislach.pages.dev/"):
    try:
        r = s.get(u, timeout=30, allow_redirects=False); print(u, r.status_code, r.headers.get("location"), r.headers.get("x-robots-tag"))
    except Exception as e: print(u, type(e).__name__)
