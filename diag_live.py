import time, urllib.request
UA={'User-Agent':'mestovcislach.sk (info@mestovcislach.sk)'}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30); return r.status, r.read()
    except Exception as e: return getattr(e,'code',0), b''
B='https://mestovcislach.sk'
for i in range(40):
    s,b=get(B+'/datove-studio/')
    if s==200 and 'ds-suhrn'.encode() in b and b':global' not in b: break
    time.sleep(30)
print('studio',s,len(b))
s,b=get(B+'/data/obce-ukazovatele.csv'); print('csv',s,len(b),b.decode('utf-8','replace').splitlines()[0][:200] if b else '', b.count(b'\n'))
s,b=get(B+'/vlozit/datove-studio?g=studio-vysledok&u=vs&kraj=0'); print('embed',s,len(b),b'data-vlozit' in b)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br=p.chromium.launch(); pg=br.new_page(); err=[]
    pg.on('pageerror',lambda e:err.append(str(e)))
    for v in ['graf','body','mapa','tabulka']:
        pg.goto(B+f'/datove-studio/?v={v}&kraj=2'); pg.wait_for_timeout(2500)
        print(v, pg.locator('#ds-podnadpis').inner_text(), pg.locator('.ds-suhrn div').count())
    pg.goto(B+'/vlozit/datove-studio?g=studio-vysledok&u=vs&kraj=0'); pg.wait_for_timeout(2500)
    print('embed nadpis', pg.locator('#ds-nadpis').inner_text(), pg.locator('#ds-podnadpis').inner_text())
    print('chyby',err); br.close()
print('HOTOVO')
