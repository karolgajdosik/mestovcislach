import subprocess, sys, time
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
J="""(()=>{const o=document.querySelector('.pr-okno');const k=document.querySelector('.pr-kapitoly').getBoundingClientRect();const m=document.querySelector('.pr-mapa').getBoundingClientRect();const f=document.querySelector('.pr-foto').getBoundingClientRect();
return {velke:o.classList.contains('pr-velke'),max:o.classList.contains('pr-max'),fs:!!document.fullscreenElement,mapa:[Math.round(m.width),Math.round(m.height)],kap:[Math.round(k.left),Math.round(k.width),Math.round(k.height)],foto:[Math.round(f.width),Math.round(f.height)],tit:document.querySelector('.pr-titulok b').textContent}})()"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    for vw,vh,name in [(390,844,'fs_mob')]:
        pg=b.new_page(viewport={"width":vw,"height":vh}); err=[]
        pg.on("pageerror",lambda e: err.append(str(e)[:200]))
        pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
        pg.click(".pr-start"); time.sleep(6)
        pg.evaluate("document.querySelector('[data-pr=cela]').click()"); time.sleep(2); print(name,"po ⛶",pg.evaluate(J))
        pg.evaluate("document.querySelectorAll('.pr-kapitoly button')[4].click()"); time.sleep(16); print(name,"po klik 5.",pg.evaluate(J))
        try: pg.screenshot(path=f"diag/{name}.jpg",type="jpeg",quality=60,timeout=90000); print("shot ok")
        except Exception: print("shot fail")
        pg.evaluate("document.querySelector('[data-pr=cela]').click()"); time.sleep(3); print(name,"späť",pg.evaluate(J))
        print(name,"chyby",err); pg.close()
    b.close()
print("HOTOVO")
# m1
