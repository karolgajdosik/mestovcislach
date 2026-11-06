import sys, re, time
sys.path.insert(0, "scripts")
import zber_obce_t9 as t9
s = t9.relacia(); rok = 2025
h = s.get(t9.ZAKLAD.format(rok=rok), timeout=60).text
print("SUBMIT", re.findall(r'<(?:button|input)[^>]*type="submit"[^>]*>', h)[:3], re.findall(r'<button[^>]*>', h)[:3])
for args in [("", ""), ("1", ""), ("", "1"), ("1", "1")]:
    try:
        x = t9.tabulka(s, rok, "55", "6", *args); print(args, len(x), x[:1])
    except Exception as e: print(args, "ERR", e)
print("HOTOVO")
