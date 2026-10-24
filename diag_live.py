import os, time, json, urllib.request, urllib.parse
os.makedirs("diag", exist_ok=True)
out=[]
UA={"User-Agent":"mestovcislach.sk diag"}
for i in range(30):
    h=urllib.request.urlopen(urllib.request.Request("https://mestovcislach.sk/trencin/adresa/?v=%d"%time.time(),headers=UA)).read().decode()
    if "data-mesta=" in h: out.append("nova verzia: ano"); break
    time.sleep(20)
else: out.append("nova verzia: zatial nie")
def n(par):
    par={"format":"jsonv2","countrycodes":"sk","limit":"5",**par}
    time.sleep(1.2)
    return json.loads(urllib.request.urlopen(urllib.request.Request("https://nominatim.openstreetmap.org/search?"+urllib.parse.urlencode(par),headers=UA)).read())
la,lo=48.8945,18.0444
box={"viewbox":f"{lo-0.3},{la+0.2},{lo+0.3},{la-0.2}","bounded":"1"}
# len počty a typ výsledku, žiadne adresy
out.append("verejne miesto v TN: %d" % len(n({**box,"q":"Mierové námestie 1, Trenčín"})))
r=n({"q":"Hubice 171","limit":"1"})
out.append("obec mimo mesta najdena: %s, typ: %s" % (bool(r), r[0].get("addresstype") if r else "-"))
out.append("s ciarkou a mestom TN v boxe: %d" % len(n({**box,"q":"Hubice, 171, Trenčín"})))
out.append("HOTOVO")
open("diag/log.txt","w").write("\n".join(out))
