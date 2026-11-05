import subprocess,sys
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import zber_obce_vlaky as V, math
u,z=V.stiahni_gtfs()
st=V.citaj(z,"stops.txt")
print(list(st[0].keys()))
for x in st[:5]: print(x)
NM={o["kod"]:o["nazov"] for o in V.OBCE}
for x in st:
    n=x["stop_name"]
    if any(w in n for w in ["Chop","Břeclav","Kittsee","Hegyeshalom","Dolný Smokovec","Devínska N","Bytčica","Diviaky","Andač","Barca","Danielov","Hačava","Hutníky","Dubová"]):
        lat,lon=float(x["stop_lat"]),float(x["stop_lon"])
        d=sorted((math.dist(p,(lat,lon)),k) for k,p in V.POL.items() if p)[:2]
        print(x["stop_id"],n,[(NM[k],round(dd*111,1)) for dd,k in d])
print("HOTOVO")
