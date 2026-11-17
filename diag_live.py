import subprocess, sys, time, requests
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
for i in range(60):
    if 'pr-kapitoly' in requests.get(U,timeout=30,headers={"Cache-Control":"no-cache"}).text: print("nasadené po",i*20,"s"); break
    time.sleep(20)
else: print("NENASADENE")
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
J="(()=>{const b=document.querySelector('.pr-titulok b').textContent;const a=document.querySelector('.pr-kapitoly .pr-akt');const m=document.querySelector('.pr').__mapa;return [b,a&&a.textContent,m&&m.getZoom().toFixed(1),document.querySelector('[data-pr=spat]').disabled,document.querySelector('[data-pr=pauza]').textContent]})()"
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":900,"height":700}); err=[]
    pg.on("pageerror",lambda e: err.append(str(e)[:200]))
    pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
    pg.click(".pr-start"); time.sleep(8)
    print("kapitoly:", pg.evaluate("[...document.querySelectorAll('.pr-kapitoly button')].map(b=>b.textContent+(b.querySelector('img')?' [foto]':''))"))
    print("štart", pg.evaluate(J))
    pg.evaluate("document.querySelector('[data-pr=dalej]').click()"); time.sleep(6); print("po ⏭", pg.evaluate(J))
    pg.evaluate("document.querySelectorAll('.pr-kapitoly button')[5].click()"); time.sleep(12); print("po klik 6.", pg.evaluate(J))
    pg.evaluate("document.querySelector('[data-pr=spat]').click()"); time.sleep(12); print("po ⏮", pg.evaluate(J))
    pg.evaluate("document.querySelector('[data-pr=pauza]').click()"); time.sleep(2); print("pauza", pg.evaluate(J))
    pg.evaluate("document.querySelector('[data-pr=dalej]').click()"); time.sleep(10); print("⏭ z pauzy", pg.evaluate(J))
    try: pg.locator(".pr").screenshot(path="diag/kap.jpg",type="jpeg",quality=60,timeout=20000)
    except Exception: print("shot fail")
    print("chyby:", err); b.close()
print("HOTOVO")
