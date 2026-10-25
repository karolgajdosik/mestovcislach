import subprocess, sys, requests, zipfile, io
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for u in ["https://volbysr.sk/oso/files/OSO2026_SK_xlsx.zip","https://volbysr.sk/osk/files/OSK2026_SK_xlsx.zip"]:
    r=requests.get(u,headers=H,timeout=120); print(u.split('/')[-1], r.status_code, r.headers.get("last-modified"), len(r.content))
    if r.ok: print("  ", sorted(zipfile.ZipFile(io.BytesIO(r.content)).namelist()))
r=subprocess.run([sys.executable, "scripts/zber_komunalne.py"], capture_output=True, text=True, timeout=1500); print("BA rc", r.returncode, r.stdout[-2500:], r.stderr[-2500:])
print("HOTOVO")
