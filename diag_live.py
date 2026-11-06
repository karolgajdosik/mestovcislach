import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt", "xlrd"])
import re
sys.path.insert(0, "scripts")
import xlrd
import zber_obce_t9 as t9
u = t9.ZAKLAD.format(rok=2025)
s = t9.relacia()
h = s.get(u, timeout=60).text
vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h).group(1)
r = s.post(u, data={"j_idt35": "j_idt35", "j_idt35:j_idt36": "j_idt35:j_idt36", "javax.faces.ViewState": vs}, headers={"Referer": u}, timeout=180)
wb = xlrd.open_workbook(file_contents=r.content)
for sh in wb.sheets():
    print("SHEET", sh.name, sh.nrows, sh.ncols)
    for i in range(min(8, sh.nrows)): print("  ", sh.row_values(i))
    print("  LAST", sh.row_values(sh.nrows - 1))
print("HOTOVO")
