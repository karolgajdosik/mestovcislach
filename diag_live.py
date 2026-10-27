import requests,time
time.sleep(150)
for u in ["https://mestovcislach.sk/trnava/volby/","https://mestovcislach.sk/bratislava/volby/","https://mestovcislach.sk/volby-2026/"]:
    t=requests.get(u+"?v=3",timeout=60).text
    print(u,"poslat-btn" in t,"Ďalej o meste" in t,"odber-form" in t)
print("HOTOVO")
