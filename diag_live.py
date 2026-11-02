import subprocess,sys; subprocess.run([sys.executable,"-m","pip","install","-q","openpyxl","requests"])
import io,re,openpyxl,requests
U="https://opendata.mfsr.sk/opendata/download/dlh-a-dlhova-sluzba-miest-a-obci-sr-k-ultimu-roka/{}"
for n in range(1,8):
    r=requests.get(U.format(n),timeout=120)
    if r.content[:2]!=b"PK": continue
    wb=openpyxl.load_workbook(io.BytesIO(r.content),read_only=True,data_only=True)
    for sh in [x for x in wb.sheetnames if "obce" in x]:
        rows=[list(x) for x in wb[sh].iter_rows(values_only=True)]
        rok=next((m.group(1) for r_ in rows[:10] for v in r_ if isinstance(v,str) and (m:=re.search(r"31\.12\.(\d{4})",v))),None)
        print("==",n,sh,rok,len(rows))
        if n==7:
            for x in rows[6:11]: print([str(v)[:40] if v is not None else None for v in x])
            print(rows[12][:16])
r=requests.get("https://opendata.mfsr.sk/",timeout=60); print(r.status_code, sorted(set(re.findall(r'/opendata/[a-z0-9\-/]+',r.text)))[:80])
print("HOTOVO")
