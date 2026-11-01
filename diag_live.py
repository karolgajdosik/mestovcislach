import subprocess,sys,json,copy
subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
def L(p):
    try: return json.load(open(p))
    except Exception: return {}
old={p:L(p) for p in ["data/obyvatelstvo-bratislava.json","data/byvanie-bratislava.json","data/mesta/temy.json"]+[f"data/mesta/{s}.json" for s in ["trnava","kosice","bratislava","presov"]]}
for cmd in (["scripts/zber_obyvatelstvo.py"],["scripts/zber_byvanie.py"],["scripts/zber_mesta.py","obyvatelia","byty","ceny"],["scripts/zber_mesta_temy.py"]):
    p=subprocess.run([sys.executable]+cmd,capture_output=True,text=True,timeout=1200); print("==",cmd,p.returncode); print(p.stdout[-900:]); print(p.stderr[-900:])
new={p:L(p) for p in old}
o,n=old["data/obyvatelstvo-bratislava.json"],new["data/obyvatelstvo-bratislava.json"]
print("BA mesto 2024/2025 staré",o["mesto"]["roky"].get("2024"),o["mesto"]["roky"].get("2025")," nové",n["mesto"]["roky"].get("2024"),n["mesto"]["roky"].get("2025"),"častí",len(n["mestske_casti"]),"kódy",[c["kod"] for c in n["mestske_casti"]][:3])
for s in ["trnava","kosice","bratislava","presov"]:
    a,b=old[f"data/mesta/{s}.json"],new[f"data/mesta/{s}.json"]
    print(s,"obyv 2025",a.get("obyvatelia",{}).get("roky",{}).get("2025"),b.get("obyvatelia",{}).get("roky",{}).get("2025"),"častí",len(b.get("obyvatelia",{}).get("casti",{})),
      "| byty 2024",a.get("byty",{}).get("2024"),b.get("byty",{}).get("2024"),"| ceny",list((a.get("ceny") or {}).items())[:1] and None)
c_old,c_new=old["data/mesta/trnava.json"].get("ceny"),new["data/mesta/trnava.json"].get("ceny")
print("ceny kľúče",type(c_old).__name__, str(c_old)[:200]); print("ceny nové",str(c_new)[:300])
bo,bn=old["data/byvanie-bratislava.json"],new["data/byvanie-bratislava.json"]
print("HPI posledné staré",bo.get("ceny",{}).get("rad",[{}])[-1]); print("HPI posledné nové",bn.get("ceny",{}).get("rad",[{}])[-1])
print("výstavba 2024 staré",bo.get("vystavba",{}).get("roky",{}).get("2024",{}).get("Bratislava"),"nové",bn.get("vystavba",{}).get("roky",{}).get("2024",{}).get("Bratislava"))
to,tn=old["data/mesta/temy.json"],new["data/mesta/temy.json"]
print("skoly trnava zs 2024",to["skoly"]["trnava"]["zs"].get("2024"),tn["skoly"]["trnava"]["zs"].get("2024"),"| ms",to["skoly"]["trnava"]["ms"].get("2024"),tn["skoly"]["trnava"]["ms"].get("2024"),"| gym",to["skoly"]["trnava"]["gym"].get("2024"),tn["skoly"]["trnava"]["gym"].get("2024"))
print("skoly kosice zs 2024",to["skoly"]["kosice"]["zs"].get("2024"),tn["skoly"]["kosice"]["zs"].get("2024"),"posledný rok",max(tn["skoly"]["kosice"]["zs"]))
nk=set(tn["mestske"]["popisy"])-set(to["mestske"]["popisy"]); print("UA nové kľúče",nk)
for k in ["st3701rr:Priemerná cena za kúpu bytu za m2","do3701rr:Dĺžka cyklistickej siete","zp3701rr:Množstvo komunálneho odpadu | kg na osobu","ku3701rr:Návštevníci múzeí za rok"]:
    print(k,to["mestske"]["mesta"]["trnava"].get(k,{}).get("2023"),tn["mestske"]["mesta"]["trnava"].get(k,{}).get("2023"),"max rok",max(tn["mestske"]["mesta"]["trnava"].get(k,{"-":0})))
print("krim Trnavský TČ 2024",tn["kriminalita"]["kraje"]["Trnavský kraj"]["Trestné činy spolu"].get("2024"),"2025",tn["kriminalita"]["kraje"]["Trnavský kraj"]["Trestné činy spolu"].get("2025"),"obyv BA kraj 2024 staré",to["kriminalita"]["obyvatelia"]["Bratislavský kraj"].get("2024"),"nové",tn["kriminalita"]["obyvatelia"]["Bratislavský kraj"].get("2024"))
print("HOTOVO")
