import subprocess, sys, time
time.sleep(470)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
J="""(()=>{const m=document.querySelector('.pr').__mapa;const z=document.querySelector('.pr-znacka');const r=document.querySelector('.pr-mapa').getBoundingClientRect();const t=document.querySelector('.pr-titulok').getBoundingClientRect();
const zb=z?z.getBoundingClientRect():null;return {pohyb:m.isMoving(),znacka:zb?[Math.round(zb.left+zb.width/2-r.left),Math.round(zb.bottom-r.top)]:null,mapa:[Math.round(r.width),Math.round(r.height)],titulokHore:Math.round(t.top-r.top),nazov:document.querySelector('.pr-titulok b').textContent}})()"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    for vw,vh,name in [(1366,768,'desk'),(390,844,'mob')]:
        pg=b.new_page(viewport={"width":vw,"height":vh})
        pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
        pg.evaluate("document.querySelector('.pr-start').click()"); time.sleep(6)
        pg.evaluate("document.querySelectorAll('.pr-kapitoly button')[3].click()")
        for k in range(12):
            time.sleep(3); s=pg.evaluate(J)
            if s['znacka']: print(name,k,s)
        pg.close()
    b.close()
print("HOTOVO")
