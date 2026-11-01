import requests,zipfile,io,json
B="https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/{}/download?type={}&lang=SK"
r=requests.get(B.format("om7101rr","JSON"),timeout=300); z=zipfile.ZipFile(io.BytesIO(r.content)); d=json.loads(z.read(z.namelist()[0]))
def sh(x,dep=0):
    if isinstance(x,dict):
        for k,v in list(x.items())[:12]: print("  "*dep+str(k), type(v).__name__, (str(v)[:120] if not isinstance(v,(dict,list)) else len(v))); 
        for k,v in list(x.items())[:6]:
            if isinstance(v,(dict,list)) and dep<2: print("  "*dep+"--",k); sh(v,dep+1)
    elif isinstance(x,list) and x: print("  "*dep+"[0]",str(x[0])[:300])
sh(d)
r=requests.get(B.format("om7102rr","CSV"),timeout=300); print("om7102rr",r.status_code,r.headers.get("content-type"),r.content[:300])
for k in ["sv5001rr","do3701rr","sk3002rr","om7102rs","om7102qr"]:
    r=requests.get(B.format(k,"CSV"),timeout=300); print(k,r.status_code,len(r.content),r.content[:2])
print("HOTOVO")
