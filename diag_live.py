import requests,re,json,io,zipfile,collections
s=requests.Session(); s.headers["User-Agent"]="mestovcislach.sk"
# EIA list
r=s.get("https://www.enviroportal.sk/api/eia_projects",params={"page":1,"itemsPerPage":5},headers={"Accept":"application/json"},timeout=60).json()
print("EIA meta",r.get("meta")); print(json.dumps(r["data"][0],ensure_ascii=False)[:1500])
# RPO search variants
for p in [{"legalForm":"801"},{"legalFormCode":"801"},{"fullName":"Obec Becherov"}]:
    try:
        x=s.get("https://api.statistics.sk/rpo/v1/search",params=p,timeout=60); print("RPO",p,x.status_code,x.text[:600])
    except Exception as e: print("RPO",p,e)
# CRZ: which zs1 look like obec, one week
cnt=collections.Counter(); ica={}
import datetime
for k in range(7):
    d=datetime.date(2026,10,19)+datetime.timedelta(days=k)
    x=s.get(f"https://www.crz.gov.sk/export/{d}.zip",timeout=120)
    if x.status_code!=200: print(d,x.status_code); continue
    z=zipfile.ZipFile(io.BytesIO(x.content))
    for m in z.namelist():
        xml=z.read(m).decode("utf-8","replace")
        for b in re.findall(r"<zmluva>(.*?)</zmluva>",xml,re.S):
            p=dict(re.findall(r"<(\w+)>(.*?)</\1>",re.sub(r"<prilohy>.*?</prilohy>","",b,flags=re.S),re.S))
            for a,i in (("zs1","ico1"),("zs2","ico")):
                n=(p.get(a) or "").strip()
                if re.match(r"(?i)obec\b|mesto\b",n): cnt["obec_"+a]+=1; ica[re.sub(r"\D","",p.get(i,""))]=n[:40]
print(cnt, "distinct obce ico", len(ica)); print(list(ica.items())[:10])
print("tags", sorted(p.keys()))
print("HOTOVO")
