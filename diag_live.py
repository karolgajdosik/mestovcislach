import requests, time, re
UA={"User-Agent":"mestovcislach.sk diag"}
B="https://mestovcislach.sk"
for i in range(30):
    h=requests.get(B+"/?v=%d"%time.time(),headers=UA,timeout=30).text
    if "VolebnaNoc" in h or 'class="vn"' in h or "vn-mesta" in h: break
    time.sleep(20)
print("úvod – upútavka:", "vn-mesta" in h)
for u in ["/trnava/stvrte","/presov/stvrte","/bratislava/stvrte","/porovnanie","/kosice/kviz"]:
    r=requests.get(B+u,headers=UA,timeout=30); og=re.search(r'og:image" content="([^"]+)',r.text)
    print(u, r.status_code, "mapa:" , "st-mapa" in r.text, "og:", og and og.group(1))
# odber: len neplatné vstupy, žiadna skutočná adresa
for telo in [{"email":"neplatna-adresa","kanal":"kosice","suhlas":True},{"email":"","kanal":"x","suhlas":False},{"web":"robot"}]:
    r=requests.post(B+"/api/odber",json=telo,headers=UA,timeout=30); print("odber", list(telo), r.status_code, r.text[:80])
print("HOTOVO")
