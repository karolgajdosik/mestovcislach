import subprocess, sys, time
time.sleep(480)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/videozona/"
I="(()=>{const s=document.querySelector('#video');return {skryta:s.hidden,nadpis:s.querySelector('h2').textContent.trim(),video:!!s.querySelector('.pv-video canvas'),prelet:!!s.querySelector('.pr .pr-start'),url:location.search,stav:document.getElementById('vz-stav').hidden?'':document.getElementById('vz-stav').textContent}})()"
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--autoplay-policy=no-user-gesture-required"])
    for vw,vh,name in [(1366,850,'desk'),(390,844,'mob')]:
        pg=b.new_page(viewport={"width":vw,"height":vh}); err=[]
        pg.on("pageerror",lambda e: err.append(str(e)[:200]))
        pg.goto(U,timeout=90000,wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
        print(name,"tipy:",pg.evaluate("[...document.querySelectorAll('.vz-karta b')].map(b=>b.textContent)"))
        pg.screenshot(path=f"diag/vz_{name}_uvod.jpg",type="jpeg",quality=60)
        pg.click("#vz-q"); pg.keyboard.type("kremn",delay=60); time.sleep(1.5)
        print(name,"návrhy:",pg.evaluate("[...document.querySelectorAll('#vz-navrhy li')].map(l=>l.textContent)"))
        pg.screenshot(path=f"diag/vz_{name}_navrhy.jpg",type="jpeg",quality=60)
        pg.keyboard.press("Enter"); time.sleep(4); print(name,"po výbere:",pg.evaluate(I))
        pg.evaluate("document.querySelector('#video [data-v=hraj]').click()"); time.sleep(3)
        print(name,"video hrá:",pg.evaluate("document.querySelector('#video [data-v=hraj]').textContent"))
        pg.evaluate("document.querySelector('#video .pr-start').click()"); time.sleep(10)
        print(name,"prelet:",pg.evaluate("(()=>{const o=document.querySelector('#video .pr-okno');return [o.hidden,document.querySelectorAll('#video .pr-kapitoly button').length,document.querySelector('#video .pr-titulok b').textContent]})()"))
        try: pg.screenshot(path=f"diag/vz_{name}_prelet.jpg",type="jpeg",quality=60,timeout=60000)
        except Exception: print('shot fail')
        # iné miesto cez kartu tipu
        pg.evaluate("document.querySelectorAll('.vz-karta')[1].click()"); time.sleep(5); print(name,"druhé:",pg.evaluate(I), pg.evaluate("document.querySelectorAll('canvas.maplibregl-canvas').length"))
        pg.evaluate("document.getElementById('vz-nahoda').click()"); time.sleep(5); print(name,"náhoda:",pg.evaluate(I))
        print(name,"chyby",err); pg.close()
    pg=b.new_page(); pg.goto(U+"?m=%2Fkosice%2F",timeout=90000); time.sleep(6); print("priamy odkaz:",pg.evaluate(I)); pg.close()
    b.close()
print("HOTOVO")
