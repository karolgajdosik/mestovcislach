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
print("TABDIV", re.findall(r'<div id="skolat9[^>]*>', x)[:2])
print("VSFORMS", re.findall(r'<input[^>]*ViewState[^>]*>', x)[:3])
vs2 = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', x).group(1)
tid = "skolat9-table-form:j_idt32"; form = "skolat9-table-form"
for rows in ["5000", "20"]:
    d = {"javax.faces.partial.ajax": "true", "javax.faces.source": tid, "javax.faces.partial.execute": tid, "javax.faces.partial.render": tid,
         tid + "_pagination": "true", tid + "_first": "20", tid + "_rows": rows, tid + "_encodeFeature": "true", form: form, "javax.faces.ViewState": vs2}
    r2 = s.post(u, data=d, headers={"Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest", "Referer": u}, timeout=120)
    print("AJAX", rows, r2.status_code, len(r2.text), r2.text[:600].replace("\n", " "), "TR", len(re.findall("<tr", r2.text)))
print("HOTOVO")
