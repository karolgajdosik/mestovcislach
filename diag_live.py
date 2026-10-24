import requests, json
UA={"User-Agent":"mestovcislach.sk"}
for u in ["https://opendata.kosice.sk/api/search/v1/collections/dataset/items?q=hlasovania&limit=20",
          "https://opendata.kosice.sk/api/v3/datasets?q=hlasovania&page[size]=20"]:
    try:
        r=requests.get(u,headers=UA,timeout=60); print("==",u,r.status_code)
        j=r.json()
        for f in (j.get("features") or j.get("data") or [])[:20]:
            p=f.get("properties") or f.get("attributes") or {}
            print("  ", f.get("id"), "|", p.get("title") or p.get("name"))
    except Exception as e: print(u,"ERR",e)
it=requests.get("https://www.arcgis.com/sharing/rest/content/items/10471bb4ff0f47879af2a861f98e34c5",params={"f":"json"},headers=UA,timeout=60).json()
print("ITEM", it.get("title"), it.get("owner"), it.get("orgId"))
r=requests.get("https://www.arcgis.com/sharing/rest/search",params={"f":"json","q":f'hlasovania orgid:{it.get("orgId")}',"num":30},headers=UA,timeout=60).json()
for x in r.get("results",[]): print("  S", x["id"], "|", x["title"], "|", x["type"])
print("HOTOVO")
