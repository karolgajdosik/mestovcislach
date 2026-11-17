import subprocess, sys
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/trenciansky-kraj/prievidza/prievidza/"
with sync_playwright() as p:
    b=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"])
    pg=b.new_page(viewport={"width":1280,"height":900}); log=[]
    pg.on("console",lambda m: log.append(m.text[:200]))
    pg.goto(U); pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(1500)
    print("reduced motion:", pg.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
    pg.evaluate("""()=>{const t0=performance.now();const b=document.querySelector('.pr-titulok');new MutationObserver(()=>console.log('T+'+Math.round((performance.now()-t0)/1000)+'s '+b.textContent.slice(0,60))).observe(b,{subtree:true,childList:true,characterData:true});}""")
    pg.click(".pr-start")
    for k in range(6):
        pg.wait_for_timeout(8000)
        pg.locator(".pr-okno").screenshot(path=f"diag/p{k}.jpg",type="jpeg",quality=60)
    print("\\n".join(log[:40])); b.close()
print("HOTOVO")
