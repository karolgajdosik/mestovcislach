import requests,time
for lau in ["SK0101528595","SK0102529320","SK0105529460"]:
    t=time.time()
    try:
        r=requests.get(f"https://rageo.minv.sk/opendata/dataset/address_by_lau2_{lau}.geojson",timeout=300,headers={"User-Agent":"mestovcislach.sk (info@mestovcislach.sk)"})
        print(lau,r.status_code,len(r.content),round(time.time()-t,1),"s",r.headers.get("content-type"))
    except Exception as e: print(lau,"ERR",e)
r=requests.get("https://rageo.minv.sk/opendata/dataset/",timeout=60);print("index",r.status_code,len(r.content))
print("HOTOVO")
