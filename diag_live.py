import subprocess,sys,json,requests,re
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
for rok in ("2026","2027"):
    p=subprocess.run([sys.executable,"scripts/zber_rozpocty.py",rok],capture_output=True,text=True,timeout=900); print(rok,p.stdout[-700:],p.stderr[-300:])
    d=json.load(open(f"data/rozpocty-{rok}.json"))
    for s in ("presov","banska-bystrica"):
        for x in d["mesta"][s]["dokumenty"][:4]: print("  ",s,x["druh"],x["zverejnene"],x["nazov"][:80])
h=requests.get("https://egov.presov.sk/Default.aspx?NavigationState=440:0:",timeout=40).text
print("rozpo odkazy:",[re.sub('<[^>]+>','',m.group(2)).strip()[:60] for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',h,re.S) if re.search('rozpo',m.group(0),re.I)][:15])
print("HOTOVO")
