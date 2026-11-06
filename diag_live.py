import subprocess, sys, re
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright"], check=True)
subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True, capture_output=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    urls = []
    pg.on("request", lambda r: urls.append(r.url) if "/rest/" in r.url else None)
    pg.goto("https://rozpocet.sk/web/#/cms/clanok/61/SK/rozpocet-sk-dokumentacia-open-api", wait_until="networkidle", timeout=90000)
    pg.wait_for_timeout(4000)
    t = pg.inner_text("body"); print("DOC", re.sub(r"\s+", " ", t)[:5000])
    print("LINKS", [a for a in pg.eval_on_selector_all("a", "e=>e.map(x=>x.href)") if "api" in a.lower() or "swagger" in a.lower() or "doc" in a.lower()][:30])
    for u in ["https://rozpocet.sk/web/#/rozpocet/SAM/kraj/0/obec/804045/prehlad", "https://rozpocet.sk/web/#/rozpocet/SAM/kraj/0/obec/804045/vydavky/f/2025/DEBT/FK"]:
        urls.clear(); pg.goto(u, wait_until="networkidle", timeout=90000); pg.wait_for_timeout(5000)
        print("PAGE", u); [print("  XHR", x) for x in urls]
        print("  TABS", [a for a in pg.eval_on_selector_all("a", "e=>e.map(x=>x.getAttribute('href')||'')") if "804045" in a][:30])
    b.close()
print("HOTOVO")
