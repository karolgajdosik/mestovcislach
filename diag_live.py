import subprocess, ssl, socket, json, urllib.request
UA={'User-Agent':'mestovcislach.sk (info@mestovcislach.sk)'}
for u in ['https://mestovcislach.sk/','https://mestovcislach.sk/datove-studio/','https://mestovcislach.sk/api/kviz','https://mestovcislach.sk/vlozit/datove-studio?g=studio-vysledok','https://mestovcislach.sk/.well-known/security.txt','https://mestovcislach.sk/neexistuje-xyz','http://mestovcislach.sk/','https://www.mestovcislach.sk/','https://mestovcislach.pages.dev/']:
    print('=====',u)
    print(subprocess.run(['curl','-sS','-o','/dev/null','-D','-','-A',UA['User-Agent'],'--max-time','20',u],capture_output=True,text=True).stdout.strip()[:1500])
ctx=ssl.create_default_context()
with socket.create_connection(('mestovcislach.sk',443)) as s:
    with ctx.wrap_socket(s,server_hostname='mestovcislach.sk') as t:
        c=t.getpeercert(); print('TLS',t.version(),c['notAfter'],c['issuer'])
for v in ['TLSv1','TLSv1.1']:
    r=subprocess.run(['curl','-sS','-o','/dev/null','-w','%{http_code}','--tlsv1.0' if v=='TLSv1' else '--tlsv1.1','--tls-max',v.replace('TLSv','').replace('1','1.0') if v=='TLSv1' else '1.1','https://mestovcislach.sk/'],capture_output=True,text=True); print(v,'->',r.stdout,r.stderr.strip()[:100])
print(subprocess.run(['curl','-sS','https://mestovcislach.sk/robots.txt'],capture_output=True,text=True).stdout[:600])
print('HOTOVO')
