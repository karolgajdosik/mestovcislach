import requests, time
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for i in range(30):
    r=requests.get("https://mestovcislach.sk/api/suboj?den=2026-10-24",headers=H,timeout=30)
    if r.status_code==200: break
    time.sleep(30)
print("api/suboj", r.status_code, r.text[:200])
print("HOTOVO")
