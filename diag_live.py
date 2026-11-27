import subprocess, sys
subprocess.run([sys.executable,'-m','pip','install','-q','playwright'],check=True)
subprocess.run([sys.executable,'-m','playwright','install','--with-deps','chromium'],check=True,capture_output=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch()
    for u in ['/videozona/?lang=hu','/datove-studio/?lang=hu']:
        pg=b.new_page(viewport={'width':1600,'height':1000}); err=[]
        pg.on('pageerror',lambda e:err.append(str(e)[:200]))
        pg.goto('https://mestovcislach.sk'+u,wait_until='networkidle'); pg.wait_for_timeout(12000)
        side=pg.evaluate("[...document.querySelectorAll('aside.bocne li a span, aside.bocne .rz-nadpis, aside.bocne p')].map(e=>e.textContent.trim()).filter(Boolean).slice(0,20)")
        print(u,'BOK',side)
        if 'videozona' in u:
            print(' karty',pg.evaluate("[...document.querySelectorAll('.vz-karta b')].slice(0,5).map(e=>e.textContent)"), pg.evaluate("[...document.querySelectorAll('.vz-mesta a')].map(e=>e.textContent)"))
        else:
            print(' studio',pg.evaluate("[...document.querySelectorAll('.ds-lbl, .ds-zalozky button, .ds-obl b')].slice(0,16).map(e=>e.textContent.trim())"))
        print(' chyby',err)
        pg.screenshot(path='diag/hu_'+('vz' if 'video' in u else 'ds')+'.png')
    b.close()
print('HOTOVO')
