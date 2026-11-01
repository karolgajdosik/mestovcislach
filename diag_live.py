import requests,zipfile,io,csv,json
B="https://statdata.statistics.sk/public/api/dc"
def rows(k):
    r=requests.get(f"{B}/opendata/cube/dataset/{k}/download?type=CSV&lang=SK",timeout=300)
    if r.content[:2]!=b"PK": return None
    z=zipfile.ZipFile(io.BytesIO(r.content)); return list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8-sig","replace"))))
for k in ("sk3002rr","sk3003rr"):
    print(k,[(x["e_year"],x["hodnota"]) for x in rows(k) if x["e_nuts13"]=="Trnavský kraj" and x["e_year"] in ("2023","2024")])
for k in ["om7103rr","om7104rr","om7105rr","om7106rr","om7001rr","om7002rr","om7009rr","om7011rr","om7012rr","om7013rr","om7014rr","om7015rr","om7016rr","om7017rr","om7018rr","om7019rr","om7020rr","om2001rr","om7107rr"]:
    rr=rows(k)
    if rr: print(k,len(rr),list(rr[0].keys()), rr[0])
for body in ({"text":"obyvateľstvo kraj"},{"searchText":"obyvateľstvo"},{"query":"obyvateľstvo"},{"fulltext":"obyvateľstvo"}):
    try:
        r=requests.post(f"{B}/search/dataCube/sk",json=body,timeout=60); print(body,r.status_code,r.text[:400])
    except Exception as e: print(body,e)
print("HOTOVO")
