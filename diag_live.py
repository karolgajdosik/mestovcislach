import sys, requests, subprocess
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_komunalne as z
UA={"User-Agent":"mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"}
for nazov,u in [("2026 OSO","https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip"),("2026 OSK","https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip"),
                ("2022 OSO xlsx","https://web.archive.org/web/20241201215347id_/https://volby.statistics.sk/oso/oso2022/files/OSO2022_SK_xlsx.zip")]:
    r=requests.get(u,headers=UA,timeout=120); print("==",nazov,r.status_code,len(r.content))
    if r.status_code!=200 or r.content[:2]!=b"PK": continue
    import zipfile,io
    print("  subory:", zipfile.ZipFile(io.BytesIO(r.content)).namelist())
    t=z.tabulky_z_balika(r.content)
    for k,v in sorted(t.items()):
        print("  ",k,len(v), sorted(v[0].keys())[:25] if v else [])
print("HOTOVO")
