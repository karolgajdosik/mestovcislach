import subprocess, sys, json
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
HTML="""<!doctype html><html><head><link rel=stylesheet href="https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css"><script src="https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js"></script>
<style>html,body,#m{margin:0;width:1280px;height:720px}</style></head><body><div id=m></div><script>
window.stav={chyby:[]};
(async()=>{
 const style=await fetch('https://tiles.openfreemap.org/styles/liberty').then(r=>r.json());
 style.sources.dem={type:'raster-dem',tiles:['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],tileSize:256,encoding:'terrarium',maxzoom:14};
 const map=new maplibregl.Map({container:'m',style,center:[18.6249,48.7743],zoom:14.2,pitch:62,bearing:-20,maxPitch:78,canvasContextAttributes:{preserveDrawingBuffer:true}});
 map.on('error',e=>stav.chyby.push(String(e.error&&e.error.message||e)));
 map.on('load',()=>{map.setTerrain({source:'dem',exaggeration:1.5});});
 map.once('idle',()=>{ setTimeout(()=>{ const f=map.querySourceFeatures('openmaptiles',{sourceLayer:'poi'}); stav.poi=f.filter(x=>x.properties.name).slice(0,40).map(x=>x.properties.class+':'+x.properties.name); stav.vyska=map.queryTerrainElevation?map.queryTerrainElevation([18.6249,48.7743]):null; stav.hotovo=true;},3000); });
})().catch(e=>{stav.chyby.push(String(e));stav.hotovo=true});
</script></body></html>"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":1280,"height":720})
    pg.set_content(HTML)
    pg.wait_for_function("window.stav && window.stav.hotovo", timeout=90000)
    s=pg.evaluate("window.stav")
    print("chyby:",s.get("chyby")[:5]); print("výška terénu v strede:",s.get("vyska")); print("body záujmu:",len(s.get("poi") or []), (s.get("poi") or [])[:15])
    pg.screenshot(path="diag/prelet.jpg",type="jpeg",quality=70)
    b.close()
print("HOTOVO")
