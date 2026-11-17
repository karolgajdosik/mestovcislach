import requests, json
r=requests.get("https://api.github.com/repos/osmlab/editor-layer-index/contents/sources/europe/sk",timeout=60).json()
for f in r:
    if f["name"].endswith(".geojson"):
        j=requests.get(f["download_url"],timeout=60).json()["properties"]
        print(f["name"], "|", j.get("name"), "|", j.get("type"), "|", j.get("url")[:300], "| licencia:", j.get("license_url") or j.get("attribution",{}).get("text"))
print("HOTOVO")
