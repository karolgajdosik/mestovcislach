import requests, json
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
d = requests.get("https://statdata.statistics.sk/public/api/dc/v3/api-docs", headers=H, timeout=60).json()
for p in ["/export/{id}/{exportType}/{lang}", "/opendata/cube/dataset/{dataCubePublicId}/rows/{rows}/columns/{columns}/context/{context}", "/public/{dimensionId}/dimensionCodeItems"]:
    print(p, json.dumps(d["paths"].get(p), ensure_ascii=False)[:1500])
sch = d.get("components", {}).get("schemas", {})
for k in sch:
    if any(w in k.lower() for w in ("export", "selection", "filter")):
        print(k, json.dumps(sch[k], ensure_ascii=False)[:1200])
print("HOTOVO")
