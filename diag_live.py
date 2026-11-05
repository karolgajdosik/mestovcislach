import re, requests
H = {"User-Agent": "Mozilla/5.0 mestovcislach.sk"}
def g(u, **kw):
    try:
        r = requests.get(u, headers=H, timeout=60, **kw); return r
    except Exception as e:
        print("ERR", u, e); return None
# 1 ÚPSVaR open data
for u in ["https://www.upsvr.gov.sk/statistiky/open-data.html", "https://www.upsvr.gov.sk/statistiky/open-data/", "https://www.upsvr.gov.sk/statistiky/nezamestnanost-mesacne-statistiky/2026.html?page_id=1254"]:
    r = g(u)
    if r is not None:
        print(u, r.status_code); print(sorted(set(re.findall(r'href="([^"]+\.(?:json|csv|xlsx?|zip))"', r.text, re.I)))[:80])
# 3 ITMS
for u in ["https://opendata.itms2014.sk/v2/projekty/ukoncene?limit=1", "https://opendata.itms2014.sk/v2/subjekty?limit=1", "https://opendata.itms21.sk/", "https://opendata.itms21.sk/v1/projekty?limit=1", "https://itms21.sk/opendata/"]:
    r = g(u)
    if r is not None: print(u, r.status_code, r.text[:600].replace("\n", " "))
# 4 školy
for u in ["https://www.cvtisr.sk/skolstvo/regionalne-skolstvo/adresar-skol.html?page_id=9599", "https://www.minedu.sk/data/att/", "https://data.slovensko.sk/api/3/action/package_search?q=%C5%A1k%C3%B4l&rows=20", "https://data.slovensko.sk/api/3/action/package_search?q=odpad%20vytriedenia&rows=20", "https://data.slovensko.sk/api/3/action/package_search?q=uch%C3%A1dza%C4%8Di%20obce&rows=20"]:
    r = g(u)
    if r is None: continue
    print(u, r.status_code)
    if "package_search" in u and r.ok:
        for p in r.json()["result"]["results"]:
            print("  ", p["name"], "|", p["title"][:90], "|", (p.get("organization") or {}).get("title", "")[:40], [x.get("format") for x in p.get("resources", [])][:5])
    else:
        print(sorted(set(re.findall(r'href="([^"]+\.(?:csv|xlsx?|zip))"', r.text, re.I)))[:30])
print("HOTOVO")
