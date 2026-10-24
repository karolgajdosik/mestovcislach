import subprocess, shutil, os, json
r = subprocess.run(["python", "scripts/zber_mesta.py", "scitanie", "volby"], capture_output=True, text=True, timeout=3000)
print("rc", r.returncode); print("\n".join(l for l in r.stdout.splitlines() if l.startswith(("  ", "OK", "::"))))
print(r.stderr[-1500:])
os.makedirs("diag", exist_ok=True)
for s in ("kosice", "bratislava"):
    shutil.copy(f"data/mesta/{s}.json", f"diag/{s}.json")
    d = json.load(open(f"data/mesta/{s}.json"))
    c = d.get("casti", {})
    print(s, len(c), "častí;", sorted(c)[:30])
    print(" obyv. názvy:", sorted(d["obyvatelia"]["casti"])[:30])
