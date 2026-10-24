import requests, time, shutil
shutil.rmtree("diag/ke", ignore_errors=True); shutil.rmtree("diag/odchody", ignore_errors=True)
H={"User-Agent":"Mozilla/5.0 (mestovcislach diag)"}
for i in range(30):
    r=requests.get("https://mestovcislach.sk/presov/odchody/",headers=H,timeout=30)
    if r.status_code==200: break
    time.sleep(30)
print("presov/odchody", r.status_code)
for u in ["/bratislava/odchody/","/data/odchody/bratislava.json","/data/odchody/bratislava/hodzovo-nam.json","/data/odchody/presov/trojica.json","/og/odchody-bratislava.png"]:
    r=requests.get("https://mestovcislach.sk"+u,headers=H,timeout=30); print(u, r.status_code, len(r.content))
h=requests.get("https://mestovcislach.sk/data/hladanie.json",headers=H,timeout=30).text
print("hľadanie zastávok:", h.count("Zastávky MHD"))
print("HOTOVO")
