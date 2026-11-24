import urllib.request
UA={'User-Agent':'mestovcislach.sk (info@mestovcislach.sk)'}
for u in ['https://mestovcislach.sk/datove-studio/','https://mestovcislach.sk/data/studio/obce.json']:
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30); b=r.read()
        print(u, r.status, len(b), 'ds-filtre' in b.decode('utf-8','replace'), 'ds-u2' in b.decode('utf-8','replace'), r.headers.get('cf-cache-status'), r.headers.get('age'))
    except Exception as e: print(u,'ERR',e)
print('HOTOVO')
