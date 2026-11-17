import subprocess, sys, time, requests
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
for i in range(60):
    h=requests.get(U,timeout=30,headers={"Cache-Control":"no-cache"}).text
    if 'pr-foto' in h and 'Nov' in h and 'data-pr="hlas"' in h: print("nasadené po",i*20,"s"); break
    time.sleep(20)
else: print("NENASADENE")
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":1280,"height":900}); log=[]
    pg.on("console",lambda m: log.append(m.text[:200]))
    pg.on("pageerror",lambda e: log.append("ERR "+str(e)[:200]))
    pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
    pg.evaluate("""()=>{const t0=performance.now();const b=document.querySelector('.pr-titulok');new MutationObserver(()=>{const f=b.querySelector('.pr-foto');console.log('T+'+Math.round((performance.now()-t0)/1000)+'s '+b.querySelector('b').textContent.slice(0,50)+' | foto '+(!f.hidden)+' | '+(b.querySelector('.pr-kredit').hidden?'':'kredit'))}).observe(b,{subtree:true,childList:true,characterData:true,attributes:true});}""")
    pg.click(".pr-start")
    for k in range(6):
        pg.wait_for_timeout(12000); print(k, pg.evaluate("(()=>{const o=document.querySelector('.pr-okno');return [o.hidden,o.getBoundingClientRect().height,!!document.querySelector('.pr').__mapa]})()")); pg.screenshot(path=f"diag/r{k}.jpg",type="jpeg",quality=65,animations="disabled")
    print("hlas tlačidlo hidden:", pg.evaluate("document.querySelector('[data-pr=hlas]').hidden"), "| zdroj:", pg.evaluate("document.querySelector('.pr-zdroj').textContent")[-90:])
    seen=[]; [seen.append(l) for l in log if l not in seen]
    print("\n".join(seen[:40])); b.close()
print("HOTOVO")
# 2
