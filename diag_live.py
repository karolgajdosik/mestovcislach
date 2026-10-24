import os, time, urllib.request
os.makedirs("diag", exist_ok=True)
out=[]
for i in range(30):
    h=urllib.request.urlopen(urllib.request.Request("https://mestovcislach.sk/kosice/?v=%d"%time.time(),headers={"User-Agent":"diag"})).read().decode()
    if "dolna-lista" in h: out.append("dolna-lista: ano, menu-plne: %s" % ("menu-plne" in h)); break
    time.sleep(20)
else: out.append("dolna-lista: zatial nie")
out.append("HOTOVO")
open("diag/log.txt","w").write("\n".join(out))
