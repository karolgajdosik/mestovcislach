import subprocess, sys, time, requests, re
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
h=requests.get(U,timeout=30).text
for c in set(re.findall(r'/_astro/[^"]+\.js',h)):
    j=requests.get("https://mestovcislach.sk"+c,timeout=30).text
    if 'pr-s-fotkou' in j or 'speechSynthesis' in j: print(c, 'essential:', j.count('essential:!0'), 'fotkou', 'pr-s-fotkou' in j)
for c in set(re.findall(r'import\("([^"]*prelet[^"]*)"',h)): print("dyn",c)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":1280,"height":900}); log=[]
    pg.on("console",lambda m: log.append(m.text[:200]))
    pg.on("pageerror",lambda e: log.append("ERR "+str(e)[:200]))
    pg.on("response",lambda r: ('prelet' in r.url) and log.append("JS "+r.url[-40:]))
    pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
    pg.evaluate("""()=>{const t0=performance.now();let last=t0;setInterval(()=>{const n=performance.now();if(n-last>1500)console.log('STALL '+Math.round(n-last)+'ms at T+'+Math.round((n-t0)/1000));last=n},250);const b=document.querySelector('.pr-titulok');new MutationObserver(()=>{const f=b.querySelector('.pr-foto');const m=document.querySelector('.pr').__mapa;console.log('T+'+Math.round((performance.now()-t0)/1000)+'s '+b.querySelector('b').textContent.slice(0,40)+' | foto '+(f&&!f.hidden)+(m?' | z '+m.getZoom().toFixed(1):''))}).observe(b,{subtree:true,childList:true,characterData:true,attributes:true});}""")
    pg.click(".pr-start")
    for k in range(7):
        time.sleep(12)
        try: print(k, pg.evaluate("(()=>{const m=document.querySelector('.pr').__mapa;return m?[m.getZoom().toFixed(1),m.getBearing().toFixed(0),m.isMoving()]:null})()"))
        except Exception as e: print(k,"evaluate fail",str(e)[:80])
        try: pg.screenshot(path=f"diag/r{k}.jpg",type="jpeg",quality=60,timeout=8000)
        except Exception as e: print(k,"shot fail")
    seen=[]; [seen.append(l) for l in log if l not in seen]
    print("\n".join(seen[:60])); b.close()
print("HOTOVO")
