import subprocess, sys, re, io, zipfile
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from spolocne import s
def g(u, **kw):
    try: return s.get(u, timeout=60, **kw)
    except Exception as e: print("ERR", u, str(e)[:100]); return None
r = g("https://volby.statistics.sk/prez/prez2024/sk/subory_na_stiahnutie.html")
if r is not None: print("prez", r.status_code, sorted(set(re.findall(r'href="([^"]+\.(?:zip|csv|xlsx?))"', r.text))))
r = g("https://www.zsr.sk/sluzby-verejnosti/pre-cestujucich/fgtfs-info")
if r is not None:
    print("zsr", r.status_code, sorted(set(x for x in re.findall(r'href="([^"]+)"', r.text) if re.search(r"gtfs|zip", x, re.I))))
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", "", r.text, flags=re.S)))
    i = t.find("GTFS"); print(t[i:i+1200])
r = g("https://www.ssd.sk/planovane-odstavky?page_id=4958")
if r is not None:
    t = r.text
    for m in re.finditer(r"<form.*?</form>", t, re.S): print("FORM", re.sub(r"\s+", " ", m.group(0))[:1500])
    i = t.find("odstáv", t.find("<main") if "<main" in t else 0)
    print(re.sub(r"\s+", " ", t[t.find('id="content"'):t.find('id="content"') + 6000])[:6000])
print("HOTOVO")
