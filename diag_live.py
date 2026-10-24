# Prieskum zdrojov – vypisuje len hlavičky, počty a názvy inštitúcií (žiadne osobné údaje)
import io, csv, requests, openpyxl, re
UA={"User-Agent":"mestovcislach.sk (github.com/karolgajdosik/mestovcislach)"}
MESTA=["Bratislava","Trnava","Nitra","Trenčín","Žilina","Banská Bystrica","Prešov","Košice"]
def txt(u):
    r=requests.get(u,headers=UA,timeout=90); r.raise_for_status()
    for k in ("utf-8-sig","cp1250"):
        try: return r.content.decode(k)
        except: pass
for u in ["https://mapaskol.iedu.sk/data-set.aspx","https://www.svs.edu.sk/data-set.aspx"]:
    try:
        t=txt(u); sep=";" if t.count(";")>t.count(",") else ","
        rows=list(csv.reader(io.StringIO(t),delimiter=sep))
        print("==",u,len(rows),"riadkov"); print("HLAVICKA:",rows[0])
        print("PRIKLAD (len stlpce bez osob):", [c[:40] for c in rows[1]][:40])
    except Exception as e: print(u,"CHYBA",e)
for i in (6,7):
    u=f"https://opendata.mfsr.sk/opendata/download/vysledky-hospodarenia-obci-a-miest-sr/{i}"
    try:
        r=requests.get(u,headers=UA,timeout=120); print("==",u,r.status_code,len(r.content), r.headers.get("content-type"))
        if r.status_code!=200: continue
        wb=openpyxl.load_workbook(io.BytesIO(r.content),read_only=True,data_only=True)
        for ws in wb.worksheets:
            rows=list(ws.iter_rows(values_only=True))
            print("HAROK",ws.title,len(rows))
            for x in rows[:8]: print("  ",[str(c)[:30] for c in x[:30] if c is not None])
            for x in rows:
                s=" ".join(str(c) for c in x if c is not None)
                if re.search(r"\bTrenčín\b",s): print("  TN:",[str(c)[:25] for c in x[:40]]); break
    except Exception as e: print(u,"CHYBA",e)
print("HOTOVO")
