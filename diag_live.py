import requests,zipfile,io,csv,json
from collections import OrderedDict
B="https://statdata.statistics.sk/public/api/dc"
for k in ["st3004rr","sp3801qr","sv5001rr","sv5002rr","sv5003rr","do3701rr","zp3701rr","ku3701rr","st3701rr","sv3701rr","sk3002rr","sk3003rr"]:
    try:
        r=requests.get(f"{B}/opendata/cube/dataset/{k}/download?type=CSV&lang=SK",timeout=300)
        z=zipfile.ZipFile(io.BytesIO(r.content)); rows=list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8-sig","replace"))))
        cols=[c for c in rows[0] if c!="hodnota"]
        print("==",k,len(rows),cols)
        for c in cols:
            v=list(OrderedDict.fromkeys(x[c] for x in rows))
            print("   ",c,len(v),v[:12] if c!="e_year" else (min(v),max(v)))
    except Exception as e: print(k,type(e).__name__,str(e)[:150])
try:
    a=requests.get(f"{B}/opendata/cubes/all",timeout=120).json()
    print("cubes all type",type(a).__name__, len(a))
    s=json.dumps(a,ensure_ascii=False)
    import re
    print("om71 kódy:",sorted(set(re.findall(r'om71\d\d\w\w',s))))
    print("príklad:",json.dumps(a[0] if isinstance(a,list) else list(a.items())[:1],ensure_ascii=False)[:400])
except Exception as e: print("cubes all",type(e).__name__,e)
print("HOTOVO")
