import requests, json, re
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
for q in ["kohesio projects", "kohesio slovakia", "list of operations slovakia", "zoznam operácií"]:
    r = requests.get("https://data.europa.eu/api/hub/search/search", params={"q": q, "limit": 15, "filter": "dataset"}, headers=H, timeout=60)
    for d in r.json()["result"]["results"]:
        t = d.get("title", {}); t = t.get("en") or t.get("sk") or next(iter(t.values()), "")
        urls = [x.get("access_url", [None])[0] if isinstance(x.get("access_url"), list) else x.get("access_url") for x in d.get("distributions", [])][:4]
        print(q, "|", t[:90], "|", d.get("id"), urls)
r = requests.get("https://cohesiondata.ec.europa.eu/api/views/metadata/v1?limit=400", headers=H, timeout=60)
for d in r.json():
    if re.search(r"kohesio|operation|beneficiar|project", d.get("name", "") + d.get("description", ""), re.I):
        print("cohesion", d["id"], d["name"][:100])
print("HOTOVO")
