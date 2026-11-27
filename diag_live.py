import urllib.request,re
UA={'User-Agent':'mestovcislach.sk (info@mestovcislach.sk)'}
h=urllib.request.urlopen(urllib.request.Request('https://mestovcislach.sk/banskobystricky-kraj/zvolen/zvolen/',headers=UA)).read().decode()
js=set(re.findall(r'/_astro/prelet[^"\']+\.js',h)); print('prelet chunks',js)
for j in js:
    t=urllib.request.urlopen(urllib.request.Request('https://mestovcislach.sk'+j,headers=UA)).read().decode()
    print('worker v6' if 'maplibre-gl-worker' in t else 'stará', 'csp' in t)
for u in ['https://mestovcislach.sk/data/studio/vyvoj/obyv.json','https://mestovcislach.sk/datove-studio/?v=vyvoj']:
    r=urllib.request.urlopen(urllib.request.Request(u,headers=UA)); b=r.read(); print(u,r.status,len(b), b'ds-obec-q' in b if b'<html' in b[:200] else '')
print('HOTOVO')
