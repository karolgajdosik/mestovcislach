import requests, json
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
B="https://volbysr.sk/oso/"
def g(p):
    r=requests.get(B+p,headers=H,timeout=60); return r.status_code, (r.text[:700] if r.ok else "")
for p in ["select/tab0a/kraje.json","json/tab02a1.json","json/tab02b1.json","json/tab0d1.json","json/tab03a1.json"]:
    print(p, *g(p))
k=json.loads(requests.get(B+"select/tab0a/kraje.json",headers=H,timeout=60).text)
print(k[:2])
