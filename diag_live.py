import subprocess, sys, time, requests, re
U="https://mestovcislach.sk/trenciansky-kraj/prievidza/prievidza/"
for i in range(45):
    h=requests.get(U,timeout=30,headers={"Cache-Control":"no-cache"}).text
    css=re.findall(r'/_astro/[^"]+\.css',h)
    if any('pr-otvoreny' in requests.get("https://mestovcislach.sk"+c,timeout=30).text for c in css): print("nasadené po",i*20,"s"); break
    time.sleep(20)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":1280,"height":900}); log=[]
    pg.on("console",lambda m: log.append(m.text[:160]))
    pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
    pg.evaluate("""()=>{const t0=performance.now();const b=document.querySelector('.pr-titulok');new MutationObserver(()=>{const m=document.querySelector('.pr').__mapa;console.log('T+'+Math.round((performance.now()-t0)/1000)+'s '+b.textContent.slice(0,60)+(m?' | zoom '+m.getZoom().toFixed(1)+' pitch '+m.getPitch().toFixed(0)+' bearing '+m.getBearing().toFixed(0):''))}).observe(b,{subtree:true,childList:true,characterData:true});}""")
    pg.click(".pr-start")
    for k,w in enumerate([9000,9000,9000,9000]):
        pg.wait_for_timeout(w); m=pg.evaluate("(()=>{const m=document.querySelector('.pr').__mapa;return m?[m.getZoom(),m.getPitch(),m.getBearing()]:null})()")
        print("stav",k,m); pg.locator(".pr-okno").screenshot(path=f"diag/q{k}.jpg",type="jpeg",quality=65)
    print("\n".join(l for l in log if l.startswith('T+'))); b.close()
print("HOTOVO")
# 1794921452
