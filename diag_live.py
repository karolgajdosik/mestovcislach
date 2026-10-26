import subprocess,sys; subprocess.run([sys.executable,"-m","pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
try:
    import zber_mesta as zm, zipfile, io, csv
    r=zm.s.get(zm.STATDATA.format("om7803rr"),timeout=600); z=zipfile.ZipFile(io.BytesIO(r.content))
    rows=list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8-sig","replace"))))
    print(rows[0].keys())
    n=sorted({x["e_nuts15"] for x in rows if "Košice" in x["e_nuts15"] or "Bratislava" in x["e_nuts15"]}); print(len(n), n[:40])
    print(sorted({x["e_nuts14"] for x in rows if "Košice" in x["e_nuts14"]})[:10])
    zm.scitanie(); print("KE",len(zm.CASTI["kosice"]),list(zm.CASTI["kosice"])[:5],"BA",len(zm.CASTI["bratislava"]))
except Exception as e:
    import traceback; print(traceback.format_exc()[-600:])
print("HOTOVO")
