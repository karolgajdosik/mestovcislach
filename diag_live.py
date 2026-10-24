import os, time, json, urllib.request, urllib.parse
os.makedirs("diag", exist_ok=True)
out=[]
UA={"User-Agent":"mestovcislach.sk diag"}
for i in range(30):
    h=urllib.request.urlopen(urllib.request.Request("https://mestovcislach.sk/bratislava/mapa?v=%d"%time.time(),headers=UA)).read().decode()
    if "u-text" in h: out.append("nova verzia: ano"); break
    time.sleep(20)
else: out.append("nova verzia: zatial nie")
out.append("HOTOVO")
open("diag/log.txt","w").write("\n".join(out))
