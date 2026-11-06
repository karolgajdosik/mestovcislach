import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt", "xlrd"])
import re, io
sys.path.insert(0, "scripts")
import zber_obce_t9 as t9
u = t9.ZAKLAD.format(rok=2025)
s = t9.relacia()
h = s.get(u, timeout=60).text
vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h).group(1)
links = re.findall(r"'j_idt35:(j_idt\d+)':'j_idt35:j_idt\d+'\},''\);return false\">([^<]*)<", h)
print("LINKS", links)
for lid, nazov in links[:5]:
    r = s.post(u, data={"j_idt35": "j_idt35", f"j_idt35:{lid}": f"j_idt35:{lid}", "javax.faces.ViewState": vs}, headers={"Referer": u}, timeout=180)
    print(nazov, r.status_code, r.headers.get("content-type"), r.headers.get("content-disposition"), len(r.content), r.content[:8])
    if r.content[:4] in (b"\xd0\xcf\x11\xe0", b"PK\x03\x04"):
        import pandas as pd
        x = pd.read_excel(io.BytesIO(r.content), header=None)
        print(x.shape); print(x.head(6).to_string()[:2500])
        break
print("HOTOVO")
