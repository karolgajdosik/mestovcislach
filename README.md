# mestovcislach.sk

Otvorené dáta o slovenských mestách a obciach – prehľadne, so zdrojom pri každom údaji. Začíname Bratislavou.

## Ako to funguje

1. **Zber dát** – Python skripty v `scripts/` sťahujú dáta z verejných API a ukladajú ich do `data/*.json`.
2. **Automatizácia** – GitHub Actions (`.github/workflows/zber-dat.yml`) spúšťa zber každú noc a pri zmene dát ich commitne.
3. **Web** – statický web v [Astro](https://astro.build) (`src/`), grafy cez Chart.js.
4. **Hosting** – Cloudflare Pages po každom commite web znova zostaví a nasadí.

## Štruktúra

```
scripts/zber_obyvatelstvo.py   zber obyvateľstva (ŠÚ SR DATAcube)
data/                          dáta pre web (JSON)
src/pages/index.astro          úvodná stránka – Bratislava
src/layouts/Base.astro         spoločný vzhľad
.github/workflows/zber-dat.yml nočný zber dát
```

## Lokálne spustenie

```bash
npm install
npm run dev            # web na http://localhost:4321

pip install -r scripts/requirements.txt
python scripts/zber_obyvatelstvo.py   # stiahne aktuálne dáta
```

Potrebné: Node.js 22.12+ a Python 3.12+.

## Nasadenie na Cloudflare Pages

Cloudflare → Workers & Pages → Create → Pages → Connect to Git → repozitár `mestovcislach`:

- Framework preset: **Astro**
- Build command: `npm run build`
- Build output directory: `dist`
- Environment variable: `NODE_VERSION` = `22`

Potom v projekte → Custom domains → pridať `mestovcislach.sk` (a `www.mestovcislach.sk`).

## Zdroje dát

| Téma | Zdroj |
|---|---|
| Obyvateľstvo | [Štatistický úrad SR – DATAcube](https://data.statistics.sk/api/) (tabuľka `om7101rr`) |

Pozn.: ŠÚ SR presúva dáta do novej databázy STATdata; DATAcube sa po 15. 9. 2026 už neaktualizuje. Zberač treba neskôr prepojiť na STATdata.
