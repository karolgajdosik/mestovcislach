import subprocess, sys, time, json
time.sleep(450)
subprocess.run([sys.executable,"-m","pip","install","-q","playwright"],check=True)
subprocess.run([sys.executable,"-m","playwright","install","--with-deps","chromium"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from playwright.sync_api import sync_playwright
U="https://mestovcislach.sk/banskobystricky-kraj/banska-stiavnica/banska-stiavnica/"
with sync_playwright() as p:
    b=p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg=b.new_page(viewport={"width":1280,"height":900},accept_downloads=True); err=[]
    pg.on("pageerror",lambda e: err.append(str(e)[:200]))
    pg.goto(U,timeout=90000,wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
    pg.evaluate("document.getElementById('video').scrollIntoView()"); pg.wait_for_timeout(3000)
    snimky=json.loads(pg.evaluate("document.querySelector('.pv-video').dataset.video"))['snimky']
    typy=[s['typ'] for s in snimky]; print("snímky:",typy)
    print("zvuk možnosti:",pg.evaluate("[...document.querySelectorAll('[data-v=zvuk] option')].map(o=>o.value+(o.selected?'*':''))"))
    pg.click("[data-v=hraj]")
    k=typy.index('pamiatky') if 'pamiatky' in typy else 1
    time.sleep(k*4+2.5)
    pg.locator(".pv-platno canvas").screenshot(path="diag/video_pamiatky.jpg",type="jpeg",quality=70)
    print("stav po prehratí:",pg.evaluate("document.querySelector('[data-v=hraj]').textContent"))
    time.sleep(max(0,len(typy)*4-k*4))
    with pg.expect_download(timeout=120000) as d:
        pg.click("[data-v=stiahni]")
    d.value.save_as("diag/video.bin"); print("súbor:",d.value.suggested_filename)
    print("stav:",pg.evaluate("document.querySelector('.pv-stav').textContent")); print("chyby",err); b.close()
r=subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,codec_name","-show_entries","format=duration","-of","compact","diag/video.bin"],capture_output=True,text=True); print(r.stdout, r.stderr[:300])
r=subprocess.run(["ffmpeg","-v","error","-i","diag/video.bin","-af","volumedetect","-f","null","-"],capture_output=True,text=True); print([l for l in r.stderr.splitlines() if 'mean_volume' in l or 'max_volume' in l])
subprocess.run(["rm","-f","diag/video.bin"])
print("HOTOVO")
