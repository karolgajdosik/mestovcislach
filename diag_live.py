import subprocess, sys, time
time.sleep(480)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch()
    for vw,name in [(390,'mob'),(800,'tab'),(1366,'desk')]:
        pg=b.new_page(viewport={"width":vw,"height":700},color_scheme="dark")
        pg.goto("https://mestovcislach.sk/",timeout=90000,wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
        print(name,pg.evaluate("(()=>{const r=e=>{const b=document.querySelector(e).getBoundingClientRect();return [Math.round(b.left),Math.round(b.top),Math.round(b.width),Math.round(b.height)]};return {hladaj:r('#hladanie-otvor'),video:r('.hlava-video'),jazyk:r('.hlava-akcie')}})()"))
        pg.screenshot(path=f"diag/hlava_{name}.jpg",type="jpeg",quality=70,clip={"x":0,"y":0,"width":vw,"height":70})
        pg.close()
    b.close()
print("HOTOVO")
