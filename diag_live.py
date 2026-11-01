import requests
B="https://statdata.statistics.sk/public/api/dc"
for k in ("pr3108rr","om7101rr"):
    r=requests.get(f"{B}/opendata/cube/dataset/{k}/supported-file-types",timeout=40); print(k,r.status_code,r.text[:300])
for t in ("CSV","JSON","XLSX"):
    for l in ("SK","EN"):
        r=requests.get(f"{B}/opendata/cube/dataset/pr3108rr/download?type={t}&lang={l}",timeout=120); print(t,l,r.status_code,r.content[:80])
r=requests.get(f"{B}/public/pr3108rr/dimensions",timeout=40); print("dims",r.status_code,r.text[:600])
print("HOTOVO")
