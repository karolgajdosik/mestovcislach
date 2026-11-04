import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from zber_hospodarenie import ruz, sablona
ICA = {'Šuľa': '00650676', 'Zvolen': '00320439', 'Vrbnica': '00325988', 'Bodza': '00306371', 'Slatina nad Bebravou': '00311073', 'Zlaté Klasy': '00305839', 'Žabokreky': '00317047'}
for n, ico in ICA.items():
    ids = ruz("uctovne-jednotky", **{"zmenene-od": "2000-01-01", "ico": ico}).get("id", [])
    print(n, ico, "UJ:", ids)
    for uid in ids:
        uj = ruz("uctovna-jednotka", id=uid)
        zz = uj.get("idUctovnychZavierok") or []
        print("  ", uid, uj.get("nazovUJ"), "zrušená" if uj.get("datumZrusenia") else "", "závierok", len(zz))
        for zid in sorted(zz)[-4:]:
            z = ruz("uctovna-zavierka", id=zid)
            sab = []
            for vid in z.get("idUctovnychVykazov", [])[:3]:
                v = ruz("uctovny-vykaz", id=vid)
                sab.append(sablona(v["idSablony"])["nazov"][:40] if v.get("idSablony") else "bez šablóny/" + str(bool(v.get("obsah"))))
            print("     ", zid, z.get("obdobieOd"), z.get("obdobieDo"), "kons" if z.get("konsolidovana") else "", z.get("typ"), sab)
print("HOTOVO")
