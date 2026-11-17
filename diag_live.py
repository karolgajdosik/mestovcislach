import subprocess, sys, time, requests, re
U="https://mestovcislach.sk/bratislava/"
time.sleep(30)
for i in range(40):
    h=requests.get(U,timeout=30,headers={"Cache-Control":"no-cache"}).text
    js=set(re.findall(r'/_astro/[^"\']+\.js',h))
    ok=False
    for j in js:
        t=requests.get("https://mestovcislach.sk"+j,timeout=30).text
        if "s2cloudless_3857" in t: ok=True;break
        for k in re.findall(r'["\']\.?/?([A-Za-z0-9_.-]+\.js)["\']',t):
            if 'prelet' in k and "s2cloudless_3857" in requests.get("https://mestovcislach.sk/_astro/"+k.split('/')[-1],timeout=30).text: ok=True;break
        if ok: break
    if ok: print("nasadené po",30+i*20,"s"); break
    time.sleep(20)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":1280,"height":900}); ch=[]
    pg.on("pageerror",lambda e: ch.append(str(e)[:150]))
    pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
    pg.click(".pr-start"); pg.wait_for_selector('.pr-okno canvas',timeout=60000); pg.wait_for_timeout(9000)
    pg.click('[data-pr="pauza"]'); pg.click('[data-pr="podklad"]'); pg.wait_for_timeout(25000)
    print("tlačidlo:",pg.text_content('[data-pr="podklad"]')); print("zdroj:",pg.text_content('.pr-zdroj')[:200])
    pg.locator(".pr-okno").screenshot(path="diag/sat.jpg",type="jpeg",quality=70); print("chyby",ch[:3]); b.close()
print("HOTOVO")
