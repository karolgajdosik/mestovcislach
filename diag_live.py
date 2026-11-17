import subprocess, sys, time, requests
U="https://mestovcislach.sk/trenciansky-kraj/prievidza/prievidza/"
for i in range(60):
    if 'data-pr="podklad"' in requests.get(U,timeout=30,headers={"Cache-Control":"no-cache"}).text: print("nasadené po",i*20,"s"); break
    time.sleep(20)
else: print("nové nasadenie sa neobjavilo")
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":1280,"height":900}); chyby=[]
    pg.on("pageerror",lambda e: chyby.append(str(e)[:200])); pg.on("console",lambda m: chyby.append(m.text[:200]) if m.type=="error" else None)
    pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
    pg.click(".pr-start"); pg.wait_for_timeout(22000)
    pg.locator(".pr-okno").screenshot(path="diag/prelet_mapa.jpg",type="jpeg",quality=70)
    print("titulok:", pg.text_content(".pr-titulok"))
    pg.click('[data-pr="podklad"]'); pg.wait_for_timeout(12000)
    print("tlačidlo podkladu:", pg.text_content('[data-pr="podklad"]'))
    pg.locator(".pr-okno").screenshot(path="diag/prelet_letecka.jpg",type="jpeg",quality=70)
    print("chyby:", chyby[:8]); b.close()
print("HOTOVO")
