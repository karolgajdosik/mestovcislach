import requests,zipfile,io,csv
B="https://statdata.statistics.sk/public/api/dc"
for p in ["/v3/api-docs","/opendata/cube/dataset/om7101rr","/opendata/cube/dataset/om7101rr/metadata","/opendata/cube","/opendata/cube/list","/opendata/collection","/cube/om7101rr","/dataset/om7101rr","/opendata/cube/dataset/om7101rr/download?type=JSON&lang=SK","/opendata/cube/dataset/om7101rr/download?type=JSONSTAT&lang=SK"]:
    try:
        r=requests.get(B+p,timeout=60); print(p,r.status_code,r.headers.get("content-type"),len(r.content),r.content[:150])
    except Exception as e: print(p,type(e).__name__)
for k in ["om7101rr","sp3801qr","st3004rr","om7102rr"]:
    try:
        r=requests.get(f"{B}/opendata/cube/dataset/{k}/download?type=CSV&lang=SK",timeout=300)
        z=zipfile.ZipFile(io.BytesIO(r.content)); n=z.namelist(); t=z.read(n[0]).decode("utf-8-sig","replace")
        rows=list(csv.DictReader(io.StringIO(t)))
        print("==",k,r.status_code,len(r.content),n,len(rows)); print("  ",list(rows[0].keys())); print("  ",rows[0]); print("  ",rows[-1])
    except Exception as e: print(k,type(e).__name__,str(e)[:150])
print("HOTOVO")
