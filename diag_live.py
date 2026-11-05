import requests, json
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36", "Accept": "application/json"}
B = "https://statdata.statistics.sk/public/api/dc"
for c in ["zp3804rr", "zp3802rr"]:
    for p in [f"/public/{c}/info", f"/public/{c}/dimensions", f"/opendata/cube/meta/{c}", f"/opendata/cube/dataset/{c}/supported-file-types"]:
        r = requests.get(B + p, headers=H, timeout=60)
        print(c, p, r.status_code, r.text[:1500].replace("\n", " "))
print("HOTOVO")
