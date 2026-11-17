import subprocess, sys, time
time.sleep(480)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
J="""(()=>{const q=s=>{const r=document.querySelector(s).getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]};
return {mapa:q('.pr-mapa'),kap:q('.pr-kapitoly'),tit:q('.pr-titulok'),foto:q('.pr-foto'),znacka:!!document.querySelector('.pr-znacka'),nazov:document.querySelector('.pr-titulok b').textContent}})()"""
def klik(pg,s): pg.evaluate(f"document.querySelector('{s}').click()")
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    for vw,vh,name in [(1366,768,'n_desk'),(390,844,'n_mob')]:
        pg=b.new_page(viewport={"width":vw,"height":vh}); err=[]
        pg.on("pageerror",lambda e: err.append(str(e)[:200]))
        pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
        klik(pg,'.pr-start'); time.sleep(6)
        pg.evaluate("document.querySelectorAll('.pr-kapitoly button')[2].click()"); time.sleep(14); print(name,'bežný',pg.evaluate(J))
        try: pg.screenshot(path=f"diag/{name}.jpg",type="jpeg",quality=60,timeout=90000)
        except Exception: print('shot fail')
        if True:
            klik(pg,'[data-pr=cela]'); time.sleep(10); print(name,'zväčšený',pg.evaluate(J))
            try: pg.screenshot(path=f"diag/{name}_velke.jpg",type="jpeg",quality=60,timeout=90000)
            except Exception: print('shot fail')
        print(name,'chyby',err); pg.close()
    b.close()
print("HOTOVO")
# v2
