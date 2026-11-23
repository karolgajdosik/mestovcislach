# Týždenná kontrola živého webu (len počty, URL stránok webu, chybové hlášky, snímky – žiadne osobné údaje).
import subprocess, sys, time, json, random, re, statistics, datetime
from urllib.parse import urlparse
subprocess.run([sys.executable,"-m","pip","install","-q","playwright","requests"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
import requests
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

W="https://mestovcislach.sk"
UA="mestovcislach.sk kontrola (info@mestovcislach.sk)"
S=requests.Session(); S.headers["User-Agent"]=UA
out={"cas":datetime.datetime.utcnow().isoformat()+"Z","stranky":[],"videozona":{},"odkazy":{},"rychlost":{}}
def kratko(s): return re.sub(r"\s+"," ",str(s))[:300]

obce=S.get(W+"/data/obce.json",timeout=60).json()["obce"]
random.seed(datetime.date.today().isoformat())
vzorka=["/","/bratislava/","/kosice/","/presov/","/zilina/","/banska-bystrica/","/nitra/","/trnava/","/trencin/"]
vzorka+=[o[2] if o[2].endswith("/") else o[2]+"/" for o in random.sample(obce,10)]
mc=[]
for m in ["/bratislava/mestske-casti/","/kosice/mestske-casti/","/zilina/mestske-casti/"]:
    try:
        h=S.get(W+m,timeout=60).text
        l=sorted(set(re.findall(r'href="(%s[a-z0-9-]+/)"'%re.escape(m),h)))
        if l: mc.append(random.choice(l))
        else: print("mc bez odkazov",m)
    except Exception as e: print("mc",m,e)
vzorka+=mc+["/videozona/","/mapa-obci/","/rebricky/","/stav-dat/"]
print("obcí v obce.json:",len(obce),"| vzorka:",len(vzorka))

odkazy=set()
ARGS=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--autoplay-policy=no-user-gesture-required"]
with sync_playwright() as p:
    b=p.chromium.launch(args=ARGS)
    ctx=b.new_context(viewport={"width":1366,"height":900})
    for u in vzorka:
        pg=ctx.new_page(); chyby=[]; csp=[]; zlyhane=[]
        pg.on("pageerror",lambda e: chyby.append("pageerror: "+kratko(e)))
        def con(m):
            if m.type!="error": return
            t=kratko(m.text)
            (csp if "Content Security Policy" in t or "Content-Security-Policy" in t else chyby).append(t)
        pg.on("console",con)
        pg.on("requestfailed",lambda r: zlyhane.append(kratko(f"{r.url[:160]} {r.failure}")) if "ERR_ABORTED" not in str(r.failure) else None)
        pg.on("response",lambda r: zlyhane.append(f"{r.status} {r.url[:160]}") if r.status>=400 else None)
        t=time.time(); st=None; obr=[]
        try:
            r=pg.goto(W+u,timeout=90000,wait_until="load"); st=r.status if r else None
            for y in range(30):
                pg.evaluate("window.scrollBy(0,900)"); pg.wait_for_timeout(150)
            pg.wait_for_timeout(2500)
            obr=pg.evaluate("()=>[...document.images].filter(i=>i.complete&&i.currentSrc&&i.naturalWidth===0).map(i=>i.currentSrc.slice(0,160))")
            for a in pg.evaluate("()=>[...document.querySelectorAll('a[href]')].map(a=>a.href)"):
                pu=urlparse(a)
                if pu.netloc in ("mestovcislach.sk","www.mestovcislach.sk") and pu.scheme.startswith("http"):
                    odkazy.add((a.split("#")[0], u))
        except Exception as e:
            chyby.append("navigácia: "+kratko(e))
        z={"url":u,"stav":st,"s":round(time.time()-t,1),"js":sorted(set(chyby))[:15],"csp":sorted(set(csp))[:15],"obrazky":obr[:15],"zlyhane":sorted(set(zlyhane))[:15]}
        out["stranky"].append(z)
        print(f"{u} {st} {z['s']}s js={len(z['js'])} csp={len(z['csp'])} obr={len(obr)} zlyh={len(z['zlyhane'])}")
        for k in ("js","csp","obrazky","zlyhane"):
            for x in z[k]: print("    ",k,x)
        pg.close()

    vz={"kroky":[],"chyby":[]}
    pg=ctx.new_page()
    pg.on("pageerror",lambda e: vz["chyby"].append("pageerror: "+kratko(e)))
    pg.on("console",lambda m: vz["chyby"].append(kratko(m.text)) if m.type=="error" else None)
    try:
        pg.goto(W+"/videozona/",timeout=90000,wait_until="load")
        pg.fill("#vz-q","Kremnica"); pg.wait_for_selector("#vz-navrhy li[data-i]",timeout=20000)
        vz["kroky"].append("vyhľadanie OK: "+pg.inner_text("#vz-navrhy li[data-i]")[:80].replace("\n"," "))
        pg.click("#vz-navrhy li[data-i]")
        pg.wait_for_selector("#vz-prehravac .pv-video",timeout=30000)
        vz["kroky"].append("načítanie OK: "+pg.title())
        pg.wait_for_timeout(1500)
        pg.click("#vz-prehravac .pv-hraj"); pg.wait_for_timeout(10000)
        hs=pg.evaluate("document.querySelector('#vz-prehravac .pv-hraj').hidden")
        vz["kroky"].append(f"video spustené (tlačidlo ▶ skryté: {hs})")
        pg.locator("#vz-prehravac .pv-platno").screenshot(path="diag/web_video.jpg",type="jpeg",quality=65)
        pg.click("#vz-prehravac .pr-start"); pg.wait_for_selector("#vz-prehravac .pr-okno:not([hidden])",timeout=20000)
        pg.wait_for_timeout(20000)
        info=pg.evaluate("()=>{const o=document.querySelector('#vz-prehravac .pr-okno');return {canvas:!!o.querySelector('canvas'),titulok:(o.querySelector('.pr-titulok b')||{}).textContent||''}}")
        vz["kroky"].append(f"prelet spustený: canvas={info['canvas']} titulok='{info['titulok'][:60]}'")
        pg.locator("#vz-prehravac .pr-okno").screenshot(path="diag/web_prelet.jpg",type="jpeg",quality=65)
    except Exception as e:
        vz["chyby"].append("krok zlyhal: "+kratko(e))
        try: pg.screenshot(path="diag/web_vz_chyba.jpg",type="jpeg",quality=60)
        except Exception: pass
    vz["chyby"]=sorted(set(vz["chyby"]))[:20]
    out["videozona"]=vz; print("VIDEOZÓNA",json.dumps(vz,ensure_ascii=False,indent=1))
    pg.close(); ctx.close()

    obec=vzorka[9]
    for u in ["/",obec]:
        mer=[]
        for i in range(3):
            c=b.new_context(viewport={"width":390,"height":844},device_scale_factor=3,is_mobile=True,has_touch=True)
            pg=c.new_page()
            pg.add_init_script("window.__lcp=0;new PerformanceObserver(l=>{for(const e of l.getEntries())window.__lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});")
            try:
                pg.goto(W+u,timeout=90000,wait_until="load"); pg.wait_for_timeout(1500)
                m=pg.evaluate("""()=>{const n=performance.getEntriesByType('navigation')[0];const f=performance.getEntriesByName('first-contentful-paint')[0];const rs=performance.getEntriesByType('resource');
                  return {ttfb:Math.round(n.responseStart),fcp:f?Math.round(f.startTime):null,lcp:Math.round(window.__lcp),dcl:Math.round(n.domContentLoadedEventEnd),load:Math.round(n.loadEventEnd),kb:Math.round(rs.reduce((s,r)=>s+(r.transferSize||0),n.transferSize||0)/1024),poziadavky:rs.length}}""")
                mer.append(m)
                if i==0: pg.screenshot(path=f"diag/web_mobil_{'uvod' if u=='/' else 'obec'}.jpg",type="jpeg",quality=60)
            except Exception as e: mer.append({"chyba":kratko(e)})
            c.close()
        ok=[m for m in mer if "load" in m]
        med={k:statistics.median([m[k] for m in ok if m[k] is not None] or [0]) for k in ("ttfb","fcp","lcp","dcl","load","kb","poziadavky")} if ok else mer
        out["rychlost"][u]=med; print("RÝCHLOSŤ (ms, medián 3)",u,med)
    b.close()

zoz={}
for a,z in sorted(odkazy): zoz.setdefault(a,z)
def over(a):
    for k in range(2):
        try:
            r=S.head(a,timeout=30,allow_redirects=True)
            if r.status_code in (405,403,501): r=S.get(a,timeout=30,stream=True); r.close()
            if r.status_code<500: return a,r.status_code
        except Exception as e: r=None; err="chyba "+type(e).__name__
        time.sleep(2)
    return a,(r.status_code if r is not None else err)
with ThreadPoolExecutor(4) as ex: vys=list(ex.map(over,sorted(zoz)))
zle=[{"odkaz":a,"stav":s,"na_stranke":zoz[a]} for a,s in vys if not (isinstance(s,int) and s<400)]
out["odkazy"]={"overenych":len(vys),"nefunkcnych":len(zle),"zoznam":zle[:50]}
print("ODKAZY overených",len(vys),"nefunkčných",len(zle)); [print("  ",z) for z in zle[:50]]
json.dump(out,open("diag/web.json","w"),ensure_ascii=False,indent=1)
print("HOTOVO")
