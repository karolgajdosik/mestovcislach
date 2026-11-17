import subprocess, sys, time, requests, re
U="https://mestovcislach.sk/trenciansky-kraj/prievidza/prievidza/"
for i in range(45):
    h=requests.get(U,timeout=30,headers={"Cache-Control":"no-cache"}).text
    css=re.findall(r'/_astro/[^"]+\.css',h)
    if any('pr-max' in requests.get("https://mestovcislach.sk"+c,timeout=30).text for c in css): print("nasadené po",i*20,"s"); break
    time.sleep(20)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium","webkit"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
JS="(()=>{const o=document.querySelector('.pr-okno');const r=o.getBoundingClientRect();const c=o.querySelector('canvas');return {fs:!!document.fullscreenElement,max:o.classList.contains('pr-max'),okno:[Math.round(r.width),Math.round(r.height)],canvas:c?[c.clientWidth,c.clientHeight]:null,vp:[innerWidth,innerHeight]}})()"
with sync_playwright() as p:
    for nazov,typ,opts in [("chromium desktop",p.chromium,{"viewport":{"width":1280,"height":900}}),("webkit iPhone",p.webkit,dict(p.devices["iPhone 13"]))]:
        b=typ.launch(**({"args":["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]} if typ==p.chromium else {}))
        pg=b.new_context(**opts).new_page(); chyby=[]; pg.on("pageerror",lambda e: chyby.append(str(e)[:150]))
        pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
        pg.click(".pr-start"); pg.wait_for_selector('.pr-okno canvas',timeout=60000); pg.wait_for_timeout(4000)
        print(nazov,"pred:",pg.evaluate(JS))
        pg.click('[data-pr="cela"]'); pg.wait_for_timeout(2500)
        print(nazov,"po kliknutí:",pg.evaluate(JS))
        pg.screenshot(path=f"diag/cela_{typ.name}.jpg",type="jpeg",quality=60)
        pg.click('[data-pr="cela"]'); pg.wait_for_timeout(1500)
        print(nazov,"späť:",pg.evaluate(JS),"chyby:",chyby[:3]); b.close()
print("HOTOVO")
