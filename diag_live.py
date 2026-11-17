import subprocess, sys, time
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
J="""(()=>{const o=document.querySelector('.pr-okno').getBoundingClientRect();const c=document.querySelector('.maplibregl-canvas');const m=document.querySelector('.maplibregl-map');
return {scrollY:Math.round(scrollY),okno:[Math.round(o.top),Math.round(o.width),Math.round(o.height)],canvas:c?[c.width,c.height,c.style.width,c.style.height]:null,mapPos:m?getComputedStyle(m).position+'/'+getComputedStyle(m).overflow:null,
css:[...document.styleSheets].some(s=>{try{return [...s.cssRules].some(r=>r.selectorText&&r.selectorText.includes('maplibregl-canvas'))}catch(e){return false}}),
ovl:(()=>{const b=document.querySelector('[data-pr=dalej]').getBoundingClientRect();const e=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return e&&(e.dataset.pr||e.className)})(),
tit:document.querySelector('.pr-titulok b').textContent}})()"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    for vw,vh,name in [(1366,768,'desk'),(390,844,'mob')]:
        pg=b.new_page(viewport={"width":vw,"height":vh}); err=[]; con=[]
        pg.on("pageerror",lambda e: err.append(str(e)[:200])); pg.on("console",lambda m: m.type in('error','warning') and con.append(m.text[:150]))
        pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
        pg.click(".pr-start")
        for t in [1,3,6,10,16]:
            time.sleep(t if t==1 else 3 if t<10 else 5); print(name,t,pg.evaluate(J))
        try: pg.screenshot(path=f"diag/{name}.jpg",type="jpeg",quality=60,timeout=90000); print("shot ok")
        except Exception as e: print("shot fail")
        print(name,"chyby",err,"\n konzola",[c for c in con if 'could not be loaded' not in c][:8]); pg.close()
    b.close()
print("HOTOVO")
