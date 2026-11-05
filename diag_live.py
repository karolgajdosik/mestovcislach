import requests,re,json
s=requests.Session(); s.headers["User-Agent"]="mestovcislach-diag"
D="ebeeedf1-aca2-451a-bdc0-35d536714888"
for u in [f"https://data.slovensko.sk/api/3/action/package_show?id={D}",f"https://data.slovensko.sk/api/action/package_show?id={D}",f"https://data.slovensko.sk/datasety/{D}",f"https://data.slovensko.sk/api/sparql",f"https://data.slovensko.sk/datasety/{D}.jsonld"]:
    try:
        r=s.get(u,timeout=60); print(u,r.status_code,r.headers.get("content-type"),len(r.text))
        t=r.text
        for m in sorted(set(re.findall(r'https?://[^"\'<> ]+',t)))[:80]:
            if re.search(r'zip|gtfs|download|distribu|subor|file',m,re.I): print("  ",m)
        print("  ...", re.sub(r"\s+"," ",t[:600]))
    except Exception as e: print(u,e)
print("HOTOVO")
