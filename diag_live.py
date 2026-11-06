import re, requests, json, io
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) mestovcislach.sk", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "sk"})
try:
    r = s.get("https://rozpocet.sk/rest/api/rozpocet/polozkySumarPodurovni/SAM/210/2024/DESC/3?uroven=CELKOVY&EKV=SpoluV&ORG=11&ORG=23&ORG=22", timeout=90)
    print("API", r.status_code, r.text[:1500])
except Exception as e: print("API ERR", e)
for base in ["http://dataportal.nucem.sk", "https://dataportal.nucem.sk"]:
    u = base + "/Dataportal-web/web/vysledky/2025/testovanie/index.xhtml"
    try:
        r0 = s.get(u, timeout=60); h = r0.text
        print(base, r0.status_code, dict(s.cookies))
        vs = re.findall(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', h)[0]
        r = s.post(u, data={"j_idt10": "j_idt10", "j_idt10:predmet_input": "55", "j_idt10:kraj_input": "6", "j_idt10:okres_input": "", "j_idt10:typz_input": "1",
                            "j_idt10:zriadovatel_input": "", "j_idt10:language_input": "1", "j_idt10:j_idt29": "Vybrať", "javax.faces.ViewState": vs},
                   headers={"Referer": u, "Origin": base}, timeout=90)
        print("FORM", r.status_code, len(r.text))
        tx = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", r.text, flags=re.S)))
        i = tx.find("Názov"); print(tx[i:i+1500] if i >= 0 else tx[:1500])
        print("buttons", re.findall(r'<button[^>]*name="([^"]+)"', h))
        break
    except Exception as e: print("ERR", base, str(e)[:200])
print("HOTOVO")
