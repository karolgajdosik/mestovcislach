import requests, re
for u in ("https://mestovcislach.sk/neexistuje-xyz", "https://mestovcislach.sk/kosice/neexistuje/"):
    r = requests.get(u, timeout=30, allow_redirects=False)
    print(u, r.status_code, re.findall(r"<title>(.*?)</title>", r.text)[:1])
