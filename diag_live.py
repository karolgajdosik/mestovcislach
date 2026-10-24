import requests, time, re
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for i in range(30):
    r=requests.get("https://mestovcislach.sk/kosice/mestske-casti/",headers=H,timeout=30)
    if r.status_code==200: break
    time.sleep(30)
print("prehľad", r.status_code, "22 mestských" in r.text)
for u in ["/kosice/mestske-casti/juh/","/kosice/mestske-casti/lunik-ix/","/kosice/","/data/hladanie.json","/sukromie/"]:
    r=requests.get("https://mestovcislach.sk"+u,headers=H,timeout=30)
    print(u, r.status_code, len(r.text), ("mestske-casti/juh" in r.text) if u in ("/kosice/","/data/hladanie.json") else "", ("service worker" in r.text) if u=="/sukromie/" else "")
print("HOTOVO")
