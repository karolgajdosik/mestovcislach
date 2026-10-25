import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
for cmd in [["scripts/zber_komunalne.py"], ["scripts/zber_mesta.py","komunalne"]]:
    r=subprocess.run([sys.executable]+cmd, capture_output=True, text=True, timeout=1500)
    print("==", cmd, r.returncode); print(r.stdout[-2500:]); print(r.stderr[-3000:])
print("HOTOVO")
