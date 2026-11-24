import requests, json
for u in ["https://mestovcislach.sk/api/sutaz"]:
    r=requests.get(u,timeout=30,headers={"Cache-Control":"no-cache"}); print(u, r.status_code); print(json.dumps(r.json(),ensure_ascii=False))
print("HOTOVO")
