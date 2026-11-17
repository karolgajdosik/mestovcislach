import requests, json, re
t=requests.get("https://api.github.com/repos/osmlab/editor-layer-index/git/trees/gh-pages?recursive=1",timeout=60).json()
cesty=[x["path"] for x in t.get("tree",[]) if x["path"].startswith("sources/europe/sk/")]
print(len(cesty), cesty[:40])
for c in cesty:
    if c.endswith(".geojson"):
        j=requests.get("https://raw.githubusercontent.com/osmlab/editor-layer-index/gh-pages/"+c,timeout=60).json()["properties"]
        print(c.split("/")[-1], "|", j.get("name"), "|", j.get("type"), "|", j.get("url")[:300], "|", j.get("license_url"), "|", (j.get("attribution") or {}).get("text"))
print("HOTOVO")
