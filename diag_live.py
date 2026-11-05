import requests, json
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
B = "https://statdata.statistics.sk/public/api/dc"
for dim in ["999525c0-203e-4222-9474-dbad4291c6b5", "302208ae-547f-409b-966e-725771c582a8"]:
    r = requests.get(f"{B}/public/{dim}/dimensionCodeItems", headers=H, timeout=120)
    print(dim, r.status_code, len(r.text))
    try:
        for x in r.json():
            s = json.dumps(x, ensure_ascii=False)
            if "omunáln" in s or "Tony" in s or "tonách" in s.lower() or '"t"' in s: print("  ", s[:300])
    except Exception as e: print(e, r.text[:300])
r = requests.get(f"{B}/public/657fbf90-fe37-4c94-bfef-c89a42af6761/zp3804rr/dimensionItemsInCube", headers=H, timeout=120)
print("nuts in cube", r.status_code, r.text[:300])
r = requests.get(f"{B}/public/999525c0-203e-4222-9474-dbad4291c6b5/zp3804rr/dimensionItemsInCube", headers=H, timeout=120)
print("indic in cube", r.status_code, r.text[:1200])
print("HOTOVO")
