import subprocess, sys, time
time.sleep(480)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/trenciansky-kraj/trencin/trencin/"
J="(()=>{const m=document.querySelector('.pr').__mapa;return m.getStyle().layers.filter(l=>l.type==='fill-extrusion'||l.id==='orto').map(l=>l.id+':'+(m.getLayoutProperty(l.id,'visibility')||'visible'))})()"
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":1366,"height":768}); err=[]
    pg.on("pageerror",lambda e: err.append(str(e)[:200]))
    pg.goto(U,timeout=90000,wait_until="domcontentloaded"); pg.wait_for_timeout(4000)
    pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
    pg.evaluate("document.querySelector('.pr-start').click()"); time.sleep(8)
    print("mapa:",pg.evaluate(J))
    pg.evaluate("document.querySelector('[data-pr=podklad]').click()"); time.sleep(15)
    print("letecká:",pg.evaluate(J), pg.evaluate("document.querySelector('[data-pr=podklad]').textContent"))
    pg.evaluate("document.querySelector('[data-pr=podklad]').click()"); time.sleep(3)
    print("späť:",pg.evaluate(J)); print("chyby",err); b.close()
print("HOTOVO")
