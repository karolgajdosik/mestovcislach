import subprocess, sys, json
subprocess.run([sys.executable,'-m','pip','install','-q','playwright'],check=True)
subprocess.run([sys.executable,'-m','playwright','install','--with-deps','chromium'],check=True,capture_output=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1600,'height':1000}); err=[]; api=[]
    pg.on('pageerror',lambda e:err.append(str(e)[:200]))
    def resp(r):
        if '/api/preklad' in r.url:
            try: api.append((r.status, len(r.request.post_data or ''), (r.text()[:300])))
            except Exception as e: api.append((r.status,'?',str(e)[:80]))
    pg.on('response',resp)
    pg.goto('https://mestovcislach.sk/videozona/?lang=hu',wait_until='networkidle'); pg.wait_for_timeout(15000)
    side=pg.evaluate("[...document.querySelectorAll('aside.bocne a, aside.bocne p, aside.bocne h2, aside.bocne span')].map(e=>e.textContent.trim()).filter(Boolean).slice(0,40)")
    print('SIDE',side)
    print('lang',pg.evaluate("document.documentElement.lang"))
    print('API',len(api)); [print(' ',a) for a in api[:8]]
    print('chyby',err)
    pg.screenshot(path='diag/hu.png')
    # zisti zakázané predkov pre prvý text v bočnom paneli
    print(pg.evaluate("""(()=>{const a=document.querySelector('aside.bocne a'); if(!a) return 'nic'; const r=a.getBoundingClientRect(); return {top:r.top, tr:a.closest('[translate]')?.outerHTML.slice(0,120), hid:!!a.closest('[hidden]'), nt:!!a.closest('.notranslate')}})()"""))
    b.close()
print('HOTOVO')
