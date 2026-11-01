import requests,json
d=requests.get("https://statdata.statistics.sk/public/api/dc/v3/api-docs",timeout=60).json()
for p,v in d["paths"].items():
    for m,o in v.items(): print(m.upper(),p,"|",o.get("summary") or o.get("operationId"),"|",[x["name"] for x in o.get("parameters",[])])
print("HOTOVO")
