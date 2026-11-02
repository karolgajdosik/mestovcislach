import subprocess,sys; subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import io,time,openpyxl,json
from spolocne import s
import zber_hospodarenie as h
for n in range(1,20):
    r=s.get(h.URL_DLH.format(n),timeout=120)
    if r.status_code!=200 or r.content[:2]!=b"PK": print(n,r.status_code); continue
    wb=openpyxl.load_workbook(io.BytesIO(r.content),read_only=True,data_only=True)
    print(n, wb.sheetnames)
    if n in (1,):
        for sh in wb.sheetnames[:3]:
            rows=[list(x) for x in wb[sh].iter_rows(values_only=True)]
            print(sh,len(rows)); [print(x[:12]) for x in rows[:9]]
last=n
ica=json.load(open("data/obce/ico.json"))
t=time.time(); kod="519014"
try: print(h.roky_jednotky(ica[kod]))
except Exception as e: print("ERR",e)
print("ruz s",round(time.time()-t))
print("HOTOVO")
