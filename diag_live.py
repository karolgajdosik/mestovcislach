import requests,time
time.sleep(120)
for u in ["https://mestovcislach.sk/kosice/zastupitelstvo/","https://mestovcislach.sk/bratislava/zastupitelstvo/","https://mestovcislach.sk/trnava/zastupitelstvo/"]:
    t=requests.get(u+"?v=5",timeout=60).text; print(u,"Kto je môj poslanec" in t,"Devín, Devínska Nová Ves" in t or "Krásna" in t or "Volebný obvod č. 1" in t)
d=requests.get("https://mestovcislach.sk/data/mesta/adresa/kosice.json",timeout=60).json(); print("KE adresa zastupcovia", bool(d.get("zastupcovia")), len((d.get("zastupcovia") or {}).get("mc",{})))
print("HOTOVO")
