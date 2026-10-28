import requests,re,html
UA={"User-Agent":"Mozilla/5.0"}
h=requests.get("https://egov.presov.sk",headers=UA,timeout=40).text
print(sorted({(m.group(1),re.sub('<[^>]+>','',m.group(2)).strip()[:40]) for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',h,re.S)})[:60])
for u in ["https://cuet.slovensko.sk","https://cuet.slovensko.sk/sk/vyhladavanie?q=rozpo%C4%8Det","https://cuet.slovensko.sk/api"]:
    try:
        r=requests.get(u,headers=UA,timeout=30); print(u,r.status_code,r.headers.get("content-type"),len(r.text)); print("  ",[x for x in re.findall(r'href="([^"]+)"',r.text) if not x.startswith('#')][:40])
    except Exception as e: print(u,type(e).__name__,e)
print("HOTOVO")
