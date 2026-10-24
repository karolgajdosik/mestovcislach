import requests, re
H={"User-Agent":"Mozilla/5.0"}
def g(u, **kw):
    try:
        r=requests.get(u,headers=H,timeout=60,allow_redirects=kw.get("redir",True))
        print(u, r.status_code, r.headers.get("location"), r.headers.get("content-type"), len(r.content)); return r
    except Exception as e: print(u,"ERR",e)
g("https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/om7803rr/download?type=CSV&lang=SK", redir=False)
r=g("https://data.statistics.sk/api/v2/collection?lang=sk")
if r is not None and r.ok:
    t=r.text; print("om7803rr in datacube:", "om7803rr" in t, "om7809rr" in t, "om7819rr" in t)
    for k in ["om7803rr","om7809rr","om7806rr","om7819rr"]:
        m=re.search(r'"href":"([^"]*/dataset/%s/[^"]*)"'%k, t); print(k, m.group(1) if m else None)
for u in ["https://volby.statistics.sk/opendata/nrsr/2023/NRSR2023_SK_tab02d.csv","https://volby.statistics.sk/nrsr/nrsr2023/","https://volbysr.sk/","https://volbysr.sk/nrsr2023/","https://volby.statistics.sk/"]:
    r=g(u)
    if r is not None and r.ok and "html" in (r.headers.get("content-type") or ""):
        print(sorted(set(re.findall(r'href="([^"]*(?:csv|zip|xlsx|opendata|nrsr|ep)[^"]*)"', r.text, re.I)))[:30])
print("HOTOVO")
