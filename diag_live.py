import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
import re
sys.path.insert(0, "scripts")
import zber_obce_t9 as t9
u = t9.ZAKLAD.format(rok=2025)
F = {"j_idt10": "j_idt10", "j_idt10:predmet_input": "55", "j_idt10:kraj_input": "6", "j_idt10:okres_input": "", "j_idt10:typz_input": "",
     "j_idt10:zriadovatel_input": "", "j_idt10:language_input": ""}
tid = "skolat9-table-form:j_idt32"; form = "skolat9-table-form"
def start():
    s = t9.relacia()
    h = s.get(u, timeout=60).text
    vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h).group(1)
    r = s.post(u, data={**F, "j_idt10:j_idt29": "Vybrať", "javax.faces.ViewState": vs}, timeout=120)
    return s, re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', r.text).group(1), r.text
H = {"Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest", "Referer": u}
for name, extra, execu in [("withform", F, tid), ("execall", F, "@all"), ("formonly", {}, f"{tid} j_idt10"), ("selection", {tid + "_selection": "null"}, tid)]:
    s, vs, x = start()
    d = {"javax.faces.partial.ajax": "true", "javax.faces.source": tid, "javax.faces.partial.execute": execu, "javax.faces.partial.render": tid,
         tid + "_pagination": "true", tid + "_first": "20", tid + "_rows": "1000", tid + "_encodeFeature": "true", form: form, "javax.faces.ViewState": vs, **extra}
    r2 = s.post(u, data=d, headers=H, timeout=120)
    print(name, r2.status_code, len(r2.text), r2.text[:300].replace("\n", " "), "TR", len(re.findall("<tr", r2.text)))
# script config of datatable
print(re.findall(r"PrimeFaces.cw\('DataTable','widget_skolat9[^;]*", x)[:1])
print("HOTOVO")
