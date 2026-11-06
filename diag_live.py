import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re
sys.path.insert(0, "scripts")
import zber_obce_t9 as t9
s = t9.relacia(); u = t9.ZAKLAD.format(rok=2025)
h = s.get(u, timeout=60).text
vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h).group(1)
r = s.post(u, data={"j_idt10": "j_idt10", "j_idt10:predmet_input": "55", "j_idt10:kraj_input": "6", "j_idt10:okres_input": "", "j_idt10:typz_input": "",
                    "j_idt10:zriadovatel_input": "", "j_idt10:language_input": "", "j_idt10:j_idt29": "Vybrať", "javax.faces.ViewState": vs}, timeout=120)
x = r.text
for m in re.finditer(r'ui-datatable|ui-paginator|DataTable\(|widgetVar', x):
    print("M", x[max(0, m.start()-300):m.start()+400].replace("\n", " ")[:700]); print("---")
print([m for m in re.findall(r'<div id="([^"]+)"', x)][:40])
print("HOTOVO")
