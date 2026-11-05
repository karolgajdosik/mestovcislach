import subprocess, sys, re, io, zipfile
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from spolocne import s
def g(u, **kw):
    try: return s.get(u, timeout=60, **kw)
    except Exception as e: print("ERR", u, str(e)[:100]); return None
r = g("https://volby.statistics.sk/prez/prez2024/sk/index.html")
if r is not None:
    print("prez scripts:", re.findall(r'(?:src|href)="([^"]+)"', r.text)[:40])
    print(re.findall(r'["\']([^"\']*(?:json|data|api)[^"\']*)["\']', r.text)[:40])
for u in ["https://www.zsdis.sk/Uvod/Online-sluzby/Planovane-odstavky", "https://www.zsdis.sk/Uvod/Dodavatelia/API-sluzby", "https://www.ssd.sk/planovane-odstavky?page_id=4958", "https://www.ssd.sk/rss?page_id=6315", "https://vsds.sk/", "https://www.vsds.sk/", "https://files.mobilitydatabase.org/mdb-1832/latest.zip", "https://www.zsr.sk/files/pre-cestujucich/cestovny-poriadok/gtfs/gtfs.zip"]:
    r = g(u, allow_redirects=True)
    if r is None: continue
    t = r.text if "zip" not in u else ""
    print("\n==", u, r.status_code, r.url, len(r.content), r.content[:2])
    if t:
        print("  odkazy:", sorted(set(x for x in re.findall(r'(?:href|src|data-[a-z-]+|action|url)\s*[=:]\s*["\']([^"\']+)["\']', t) if re.search(r"odstav|prerus|api|json|xml|rss|ajax|obec|search|hlad", x, re.I)))[:40])
        txt = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S))
        txt = re.sub(r"<[^>]+>", " | ", txt)
        i = max(txt.find("Plánovan"), 0)
        print("  text:", re.sub(r"(\s*\|\s*)+", " | ", txt[i:i+1800]))
    elif r.content[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(r.content)); print("  ", [(n, z.getinfo(n).file_size) for n in z.namelist()])
        if "feed_info.txt" in z.namelist(): print(z.read("feed_info.txt")[:300])
        if "calendar.txt" in z.namelist(): print(z.read("calendar.txt")[:200])
print("HOTOVO")
