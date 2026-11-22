import subprocess, sys, time, json, os
subprocess.run("sudo apt-get install -y -qq osmium-tool >/dev/null 2>&1", shell=True)
subprocess.run([sys.executable,"-m","pip","install","-q","osmium","shapely","requests"],check=True)
sys.path.insert(0,"scripts")
os.environ["OSM_CACHE"]="/tmp/osm"
import osm_lokalne as o, requests
t0=time.time(); o.pbf(); print("pbf", round(time.time()-t0),"s")
def overpass(q):
    for u in ["https://overpass-api.de/api/interpreter","https://overpass.private.coffee/api/interpreter","https://overpass.kumi.systems/api/interpreter"]:
        try:
            r=requests.post(u,data={"data":q},timeout=300,headers={"User-Agent":"mestovcislach.sk (info@mestovcislach.sk) test"})
            if r.status_code==200: return r.json()
            print("  overpass",u,r.status_code)
        except Exception as e: print("  overpass",u,type(e).__name__)
    return None
KE=1690324  # Košice (osm_rel)
Q={
 "mapa Košice": f'[out:json][timeout:240];area({3600000000+KE})->.a;(nwr(area.a)["amenity"="pharmacy"];nwr(area.a)["amenity"~"^(hospital|clinic)$"];nwr(area.a)["historic"~"^(castle|monument|church|memorial)$"]["name"];nwr(area.a)["leisure"="playground"];);out center tags;',
 "hranica Košice": f'[out:json][timeout:120];relation({KE});out geom;',
 "časti body Košice": f'[out:json][timeout:120];area({3600000000+KE})->.a;(node(area.a)[place~"^(suburb|quarter|neighbourhood|village|hamlet)$"][name];);out;',
 "cyklo BA": open("scripts/zber_cyklo.py").read().split('DOTAZ = """')[1].split('"""')[0],
 "vybavenost BA": open("scripts/zber_vybavenost.py").read().split('DOTAZ = """')[1].split('"""')[0],
 "hranice MČ BA": open("scripts/zber_hranice.py").read().split('DOTAZ = """')[1].split('"""')[0],
 "obce SK center": '[out:json][timeout:300];area["ISO3166-1"="SK"][admin_level=2]->.sk;rel(area.sk)["boundary"="administrative"]["admin_level"~"^(9|8)$"]["ref"];out center tags;',
}
for n,q in Q.items():
    t=time.time()
    try: L=o.dopyt(q)["elements"]
    except Exception as e: print(n,"LOKÁLNE CHYBA",type(e).__name__,e); continue
    tl=time.time()-t; t=time.time(); R=overpass(q); tr=time.time()-t
    if R is None: print(f"{n}: lokálne {len(L)} ({tl:.0f}s), Overpass nedostupný"); continue
    R=R["elements"]
    sl={(e['type'],e['id']) for e in L}; sr={(e['type'],e['id']) for e in R}
    # porovnanie stredov a počtu bodov geometrie
    dl={(e['type'],e['id']):e for e in L}; dr={(e['type'],e['id']):e for e in R}
    odch=[]
    for k in sl&sr:
        a,b=dl[k],dr[k]
        pa=a.get('center') or ({'lat':a['lat'],'lon':a['lon']} if 'lat' in a else None); pb=b.get('center') or ({'lat':b['lat'],'lon':b['lon']} if 'lat' in b else None)
        if pa and pb: odch.append(abs(pa['lat']-pb['lat'])+abs(pa['lon']-pb['lon']))
        if a.get('tags')!=b.get('tags'): odch.append(-1)
    tagdiff=sum(1 for x in odch if x==-1); maxd=max([x for x in odch if x>=0] or [0])
    geo=""
    if Q[n].strip().endswith("out geom;") or "geom" in Q[n][-20:]:
        gl=sum(len(e.get('geometry',[]))+sum(len(m.get('geometry',[])) for m in e.get('members',[])) for e in L)
        gr=sum(len(e.get('geometry',[]))+sum(len(m.get('geometry',[])) for m in e.get('members',[])) for e in R)
        geo=f", body geometrie {gl} vs {gr}"
    print(f"{n}: lokálne {len(L)} ({tl:.0f}s) | Overpass {len(R)} ({tr:.0f}s) | spoločné {len(sl&sr)}, len lokálne {len(sl-sr)}, len Overpass {len(sr-sl)}, rozdiel tagov {tagdiff}, max posun stredu {maxd:.5f}°{geo}")
    if sr-sl: print("   príklady len Overpass:", sorted(sr-sl)[:5])
    if sl-sr: print("   príklady len lokálne:", sorted(sl-sr)[:5])
print("HOTOVO")
