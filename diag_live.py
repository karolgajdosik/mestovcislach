import subprocess
for v in ['-tls1','-tls1_1','-tls1_2','-tls1_3']:
    r=subprocess.run(['openssl','s_client','-connect','mestovcislach.sk:443','-servername','mestovcislach.sk',v,'-cipher','DEFAULT:@SECLEVEL=0'],input='',capture_output=True,text=True,timeout=30)
    out=r.stdout+r.stderr
    proto=[l.strip() for l in out.splitlines() if 'Protocol' in l or 'alert' in l.lower() or 'no protocols' in l.lower()][:2]
    print(v, 'OK' if 'BEGIN CERTIFICATE' in out or 'Cipher is' in out and 'Cipher is (NONE)' not in out else 'ODMIETNUTÉ', proto)
print('HOTOVO')
