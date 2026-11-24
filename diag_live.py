import requests, json, time
time.sleep(480)
B="https://mestovcislach.sk"
H={"Origin":B,"User-Agent":"Mozilla/5.0 test-pocitadla","Content-Type":"application/json"}
print("GET pred:", requests.get(B+"/api/kviz?mesiace=1",timeout=30).text[:300])
print("neplatný:", requests.post(B+"/api/kviz",data=json.dumps({"u":"start","k":"/zle"}),headers=H,timeout=30).status_code)
print("robot:", requests.post(B+"/api/kviz",data=json.dumps({"u":"start","k":"/test/kviz"}),headers={**H,"User-Agent":"Googlebot"},timeout=30).status_code)
for u in ["start","koniec"]:
    print(u, requests.post(B+"/api/kviz",data=json.dumps({"u":u,"k":"/test/kviz/"}),headers=H,timeout=30).status_code)
print("cudzí pôvod:", requests.post(B+"/api/kviz",data=json.dumps({"u":"start","k":"/test/kviz"}),headers={**H,"Origin":"https://example.com"},timeout=30).status_code)
print("GET po:", requests.get(B+"/api/kviz?mesiace=1&x=1",timeout=30).text[:300])
print("HOTOVO")
