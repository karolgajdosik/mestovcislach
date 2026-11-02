import requests,re,collections
s=requests.Session(); c=collections.Counter(); ex=[]
for p in range(1,40):
    for z in s.get("https://www.enviroportal.sk/api/eia_projects",params={"page":p,"itemsPerPage":100},headers={"Accept":"application/json"},timeout=60).json()["data"]:
        o=z.get("obec") or ""
        if "Zálužie" in z.get("name","") : print("VZ",repr(o),"|",z.get("okres"))
        if re.search(r"[,;]",o): c["multi"]+=1; ex.append((o[:150],z.get("okres"),z["name"][:60]))
        else: c["single"]+=1
print(c); 
for e in ex[:15]: print(e)
print("HOTOVO")
