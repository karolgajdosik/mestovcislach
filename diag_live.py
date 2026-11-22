# Spustí zberové skripty s lokálnym OSM a porovná výstupy s aktuálnymi dátami (len počty – žiadne osobné údaje).
import subprocess, sys, time, json, os, glob
subprocess.run("sudo apt-get install -y -qq osmium-tool >/dev/null 2>&1", shell=True)
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"],check=True)
os.environ["OSM_CACHE"]="/tmp/osm"
stare={}
for f in glob.glob("public/data/mesta/mapa-osm-*.json")+["data/mesta/casti-osm.json","data/obce/osm.json","data/obce/trasy.json","data/cyklo-bratislava.json","data/vybavenost-bratislava.json","data/hranice-bratislava.geojson"]:
    stare[f]=json.load(open(f)) if os.path.exists(f) else None
def beh(cmd):
    t=time.time(); r=subprocess.run(cmd,shell=True,capture_output=True,text=True)
    out=(r.stdout+r.stderr).strip().splitlines()
    print(f"== {cmd}: {time.time()-t:.0f} s, kód {r.returncode}")
    for l in out[-12:]: print("   ",l[:200])
for c in ["python scripts/zber_mapa_osm.py","python scripts/zber_casti_osm.py","python scripts/zber_cyklo.py","python scripts/zber_vybavenost.py","python scripts/zber_hranice.py","python scripts/zber_obce_wiki_osm.py osm trasy"]:
    beh(c)
def n(f):
    return json.load(open(f)) if os.path.exists(f) else None
print("\n== Porovnanie (staré → nové)")
for f in sorted(stare):
    a,b=stare[f],n(f)
    if a is None or b is None: print(f,"chýba",a is None,b is None); continue
    if "mapa-osm" in f:
        va={v.get('id'):len(v['body']) for v in a['vrstvy']}; vb={v.get('id'):len(v['body']) for v in b['vrstvy']}
        print(f.split('/')[-1], " ".join(f"{k.replace('osm-','')}:{va.get(k)}→{vb.get(k)}" for k in sorted(set(va)|set(vb))), "| hranica body", len(json.dumps(a['hranice'])), "→", len(json.dumps(b['hranice'])))
    elif "casti-osm" in f:
        print("casti-osm", {k:(len(a['mesta'].get(k,{}).get('casti',[])),len(v['casti'])) for k,v in b['mesta'].items()})
    elif f.endswith("osm.json"):
        sa={k:sum(v) if isinstance(v,list) else 0 for k,v in a['obce'].items()}; sb={k:sum(v) if isinstance(v,list) else 0 for k,v in b['obce'].items()}
        rozd=sorted(((abs(sb.get(k,0)-sa.get(k,0)),k) for k in set(sa)|set(sb)),reverse=True)[:5]
        print("obce/osm.json obcí",len(a['obce']),"→",len(b['obce']),"| súčet",sum(sa.values()),"→",sum(sb.values()),"| najväčšie rozdiely",rozd)
    elif f.endswith("trasy.json"):
        sa=sum(sum(v) for v in a['obce'].values()); sb=sum(sum(v) for v in b['obce'].values())
        print("obce/trasy.json obcí",len(a['obce']),"→",len(b['obce']),"| km spolu",round(sa),"→",round(sb))
    elif "cyklo" in f or "vybavenost" in f:
        print(f.split('/')[-1], "mesto:", json.dumps(a.get('mesto'))[:160], "\n    →", json.dumps(b.get('mesto'))[:160])
    else:
        print(f.split('/')[-1], "prvkov", len(a.get('features',[])), "→", len(b.get('features',[])))
print("HOTOVO")
