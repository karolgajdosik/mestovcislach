import subprocess, sys
subprocess.run([sys.executable,'-m','pip','install','-q','playwright'],check=True)
subprocess.run([sys.executable,'-m','playwright','install','--with-deps','chromium'],check=True,capture_output=True)
from playwright.sync_api import sync_playwright
for base,meno in [('https://maplibre-6.mestovcislach.pages.dev','v6'),('https://mestovcislach.sk','zive')]:
    with sync_playwright() as p:
        b=p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        pg=b.new_page(viewport={'width':1366,'height':900}); err=[]
        pg.on('pageerror',lambda e:err.append('PE '+str(e)))
        pg.on('console',lambda m: err.append('C '+m.text) if m.type=='error' else None)
        pg.goto(base+'/banskobystricky-kraj/zvolen/zvolen/',wait_until='domcontentloaded'); pg.wait_for_timeout(2500)
        pg.locator('.pr-start').first.scroll_into_view_if_needed(); pg.locator('.pr-start').first.click()
        pg.wait_for_timeout(20000)
        canv=pg.evaluate("document.querySelectorAll('.pr-mapa canvas').length")
        tit=pg.evaluate("document.querySelector('.pr-titulok b')?.textContent")
        ver=pg.evaluate("document.querySelector('.maplibregl-map') ? 'mapa ok' : 'bez mapy'")
        pg.screenshot(path=f'diag/prelet_{meno}.png')
        print(meno,'canvas',canv,ver,'titulok',tit)
        print(meno,'chyby',[e[:200] for e in err][:8])
        b.close()
print('HOTOVO')
