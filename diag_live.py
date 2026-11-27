import subprocess, json, re, urllib.request
UA='mestovcislach.sk (info@mestovcislach.sk)'
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=30)
r=get('https://mestovcislach.sk/.well-known/security.txt'); print('security.txt',r.status,r.read().decode()[:80].replace('\n',' | '))
t=get('https://mestovcislach.sk/data/mesta/mapa-kosice.json').read().decode()
print('kosice emaily',len(set(re.findall(r'[\w.+-]+@[\w-]+\.[a-z]{2,}',t))),'telefon polí',t.count('Telefon'))
# limit odberu: 7 pokusov s neplatnou adresou (Brevo sa nekontaktuje pri chybnej adrese)
for i in range(8):
    p=subprocess.run(['curl','-s','-o','/dev/null','-w','%{http_code}','-X','POST','-H','content-type: application/json','-A',UA,'-d','{"email":"neplatna","kanal":"x","suhlas":true}','https://mestovcislach.sk/api/odber'],capture_output=True,text=True)
    print('odber pokus',i+1,p.stdout)
print('HOTOVO')
