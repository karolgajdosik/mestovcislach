import requests, zipfile, io, re
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for u in ["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip","https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip","https://volbysr.sk/oso/files/OSO2026_SK_csv.zip"]:
    try:
        r=requests.get(u,headers=H,timeout=120)
        print(u.split('/')[-1], r.status_code, r.headers.get("last-modified"), len(r.content))
        if r.ok and r.content[:2]==b"PK":
            print("  ", sorted(zipfile.ZipFile(io.BytesIO(r.content)).namelist()))
    except Exception as e: print(u, "ERR", e)
for u in ["https://volbysr.sk/oso/sk/","https://volbysr.sk/"]:
    try:
        r=requests.get(u,headers=H,timeout=60); t=re.sub(r"<[^>]+>"," ",r.text)
        print(u, r.status_code, len(r.text), re.findall(r"[Ss]pracovan[^.]{0,80}", t)[:3], re.findall(r"\d{1,3}[,.]\d{1,2}\s?%", t)[:5])
    except Exception as e: print(u,"ERR",e)
print("HOTOVO")
