import subprocess, sys, re, io, zipfile
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from spolocne import s
r = s.get("https://www.zsr.sk/sluzby-verejnosti/pre-cestujucich/fgtfs-info", timeout=60)
for m in re.finditer(r"gtfs", r.text, re.I):
    print("…", re.sub(r"\s+", " ", r.text[max(0, m.start()-300):m.start()+300]))
for kolo in ("kolo1", "kolo2"):
    z = zipfile.ZipFile(io.BytesIO(s.get(f"https://volby.statistics.sk/prez/prez2024/files/{kolo}/PREZ2024_{kolo}_SK_csv.zip", timeout=120).content))
    print(kolo, [(n, z.getinfo(n).file_size) for n in z.namelist()])
    for n in z.namelist():
        if re.search(r"tab0?2d|tab03e|tab01\.|tab03d|tab02b", n, re.I):
            t = z.read(n).decode("utf-8-sig", "replace").splitlines()
            print("  ", n, t[0][:400]); print("     ", t[1][:300])
print("HOTOVO")
