import requests, re, zipfile, io
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for u in ["https://volbysr.sk/oso/sk/","https://volbysr.sk/osk/sk/","https://volbysr.sk/oso/sk/data.html","https://volbysr.sk/oso/sk/vysledky.html"]:
    try:
        r=requests.get(u,headers=H,timeout=60); r.encoding="utf-8"
        print(u, r.status_code, len(r.text))
        print("  odkazy:", sorted(set(re.findall(r'href="([^"#]+)"', r.text)))[:40])
    except Exception as e: print(u,"ERR",e)
r=requests.get("https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip",headers=H,timeout=60)
z=zipfile.ZipFile(io.BytesIO(r.content))
import openpyxl
wb=openpyxl.load_workbook(io.BytesIO(z.read("OSK2026_SK_tab_info.xlsx")),read_only=True)
for ws in wb: 
    for row in list(ws.iter_rows(values_only=True))[:6]: print("  info:", row)
print("HOTOVO")
