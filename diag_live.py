import requests
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (mestovcislach.sk diag)"
for u in ("https://mestovcislach.sk/", "https://mestovcislach.sk/kosice/"):
    t = s.get(u, timeout=30).text
    print(u, "cloudflareinsights beacon:", "cloudflareinsights" in t, "| data-cf-beacon:", "data-cf-beacon" in t)
r = s.get("https://mestovcislach.pages.dev/", timeout=30); print("pages.dev X-Robots-Tag:", r.headers.get("x-robots-tag"))
r = s.get("https://mestovcislach.sk/", timeout=30); print("hlavná X-Robots-Tag:", r.headers.get("x-robots-tag"))
