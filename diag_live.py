import requests,time
time.sleep(150)
m=requests.get("https://mestovcislach.sk/data/odber-brevo.json?v=6",timeout=30).json()
print("zoznamy týždenník:",sorted(k for k in m["zoznamy"] if k.startswith("tyzdennik-")))
d=requests.get("https://mestovcislach.sk/data/tyzdennik/kosice.json",timeout=30).json(); print("KE novinky",len(d["novinky"]),"termíny",[t["nazov"] for t in d["terminy"]])
t=requests.get("https://mestovcislach.sk/trnava/?v=6",timeout=30).text; print("formulár na prehľade","Týždenník mesta e-mailom" in t)
print("HOTOVO")
