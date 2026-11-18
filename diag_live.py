import subprocess, sys, time
time.sleep(470)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
S="(()=>{const z=document.querySelector('[data-v=zvuk]');return [z.textContent,z.getAttribute('aria-label'),!!document.querySelector('select[data-v=zvuk]')]})()"
with sync_playwright() as p:
    b=p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg=b.new_page(viewport={"width":1280,"height":900}); err=[]
    pg.on("pageerror",lambda e: err.append(str(e)[:200]))
    pg.goto(U,timeout=90000,wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
    pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(3000)
    print("na začiatku:",pg.evaluate(S))
    pg.click("[data-v=hraj]"); time.sleep(3)
    pg.click("[data-v=zvuk]"); time.sleep(1); print("po kliknutí:",pg.evaluate(S), pg.evaluate("document.querySelector('[data-v=hraj]').textContent"))
    pg.locator(".pv-video").screenshot(path="diag/video_repro.jpg",type="jpeg",quality=70)
    pg.click("[data-v=zvuk]"); time.sleep(1); print("znova:",pg.evaluate(S))
    print("chyby",err); b.close()
print("HOTOVO")
