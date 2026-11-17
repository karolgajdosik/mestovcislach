// 3D prelet nad obcou / mestskou časťou (MapLibre GL, načíta sa až po kliknutí).
// Podklad: ortofotomozaika SR (GKÚ Bratislava, CC BY 4.0), ak služba odpovie a povolí CORS; inak vektorová mapa OpenFreeMap.
// Terén: Terrain Tiles (Terrarium, AWS Open Data). Zastávky kamery: pomenované body záujmu z dlaždíc OpenMapTiles v okolí.

type Data = { nazov: string; stred: [number, number]; bbox?: [number, number, number, number] | null; km2?: number | null; titulky: [string, string][] };

const OFM = 'https://tiles.openfreemap.org';
const WMS = 'https://zbgisws.skgeodesy.sk/zbgis_ortofoto_wms/service.svc/get';
const DEM = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png';
const TRIEDY: Record<string, string> = {
  castle: 'hrad / kaštieľ', monument: 'pamätník', place_of_worship: 'kostol', town_hall: 'obecný úrad', museum: 'múzeum', attraction: 'zaujímavosť',
  theatre: 'divadlo', library: 'knižnica', school: 'škola', college: 'škola', hospital: 'nemocnica', stadium: 'štadión', park: 'park', swimming_pool: 'kúpalisko',
};
const PORADIE = Object.keys(TRIEDY);

const sOkamih = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
async function sTimeoutom<T>(p: Promise<T>, ms: number): Promise<T> {
  return Promise.race([p, new Promise<T>((_, z) => setTimeout(() => z(new Error('čas')), ms))]);
}

/** Ortofoto: názov vrstvy z GetCapabilities a skúšobná dlaždica (CORS). Vráti šablónu dlaždíc alebo null. */
async function ortofoto(lat: number, lon: number): Promise<string | null> {
  try {
    const cap = await sTimeoutom(fetch(`${WMS}?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0`, { mode: 'cors' }).then((r) => (r.ok ? r.text() : Promise.reject())), 5000);
    const doc = new DOMParser().parseFromString(cap, 'text/xml');
    const mena = [...doc.querySelectorAll('Layer > Name')].map((n) => n.textContent?.trim()).filter(Boolean) as string[];
    if (!mena.length || !/3857/.test(cap)) return null;
    const vrstva = mena[mena.length > 1 ? 1 : 0];
    const sablona = `${WMS}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=${encodeURIComponent(vrstva)}&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=512&HEIGHT=512&FORMAT=image/jpeg`;
    // skúšobná dlaždica okolo stredu obce
    const x = (lon * 20037508.34) / 180, y = (Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / 180)) * (20037508.34 / 180);
    const t = await sTimeoutom(fetch(sablona.replace('{bbox-epsg-3857}', `${x - 300},${y - 300},${x + 300},${y + 300}`), { mode: 'cors' }), 6000);
    if (!t.ok || !(t.headers.get('content-type') ?? '').startsWith('image/')) return null;
    return sablona;
  } catch {
    return null;
  }
}

export async function spustiPrelet(el: HTMLElement): Promise<void> {
  const d: Data = JSON.parse(el.dataset.prelet!);
  const okno = el.querySelector<HTMLElement>('.pr-okno')!;
  const mapaEl = el.querySelector<HTMLElement>('.pr-mapa')!;
  const tit = el.querySelector<HTMLElement>('.pr-titulok')!;
  const tlPauza = el.querySelector<HTMLButtonElement>('[data-pr="pauza"]')!;
  const zdroj = el.querySelector<HTMLElement>('.pr-zdroj')!;
  okno.hidden = false;
  el.querySelector<HTMLElement>('.pr-uvod')!.hidden = true;
  const titulok = (b: string, s = '') => { tit.querySelector('b')!.textContent = b; tit.querySelector('span')!.textContent = s; tit.classList.toggle('pr-skryty', !b); };
  titulok('Načítavam mapu…');

  const [lat, lon] = d.stred;
  const [mod, worker, orto] = await Promise.all([
    import('maplibre-gl/dist/maplibre-gl-csp.js' as string),
    import('maplibre-gl/dist/maplibre-gl-csp-worker.js?url' as string).then((m) => m.default as string),
    ortofoto(lat, lon),
    // štýly MapLibre ako samostatný súbor až pri spustení (inak by Astro pridalo 70 kB CSS do hlavičky každej obce)
    import('maplibre-gl/dist/maplibre-gl.css?url' as string).then((m) => new Promise<void>((ok) => {
      const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = m.default; l.onload = () => ok(); l.onerror = () => ok(); document.head.append(l);
    })),
  ]);
  const maplibregl: any = mod.default ?? mod;
  maplibregl.setWorkerUrl(worker);

  // štýl: ortofoto + názvy z OpenMapTiles, alebo celá vektorová mapa OpenFreeMap
  let style: any;
  if (orto) {
    style = {
      version: 8, glyphs: `${OFM}/fonts/{fontstack}/{range}.pbf`,
      sources: {
        orto: { type: 'raster', tiles: [orto], tileSize: 512, maxzoom: 19, attribution: 'Ortofotomozaika SR © GKÚ Bratislava, ÚGKK SR (CC BY 4.0)' },
        openmaptiles: { type: 'vector', url: `${OFM}/planet`, attribution: '© OpenMapTiles, údaje © prispievatelia OpenStreetMap' },
      },
      layers: [
        { id: 'orto', type: 'raster', source: 'orto' },
        { id: 'miesta', type: 'symbol', source: 'openmaptiles', 'source-layer': 'place', filter: ['in', ['get', 'class'], ['literal', ['city', 'town', 'village', 'suburb', 'hamlet']]],
          layout: { 'text-field': ['coalesce', ['get', 'name:sk'], ['get', 'name']], 'text-font': ['Noto Sans Bold'], 'text-size': 15 }, paint: { 'text-color': '#fff', 'text-halo-color': 'rgba(0,0,0,0.75)', 'text-halo-width': 1.6 } },
      ],
    };
  } else {
    style = await fetch(`${OFM}/styles/liberty`).then((r) => r.json());
  }
  style.sources.dem = { type: 'raster-dem', tiles: [DEM], tileSize: 256, encoding: 'terrarium', maxzoom: 14, attribution: 'Terén: Terrain Tiles (Mapzen, AWS Open Data)' };
  // tieňovaný reliéf (samostatný zdroj – MapLibre odporúča nezdieľať zdroj terénu a tieňovania)
  style.sources.demhs = { type: 'raster-dem', tiles: [DEM], tileSize: 256, encoding: 'terrarium', maxzoom: 14 };
  const prvaCiara = style.layers.findIndex((l: any) => l.type === 'line' || l.type === 'symbol' || l.type === 'fill-extrusion');
  style.layers.splice(orto ? 1 : Math.max(1, prvaCiara), 0, { id: 'relief', type: 'hillshade', source: 'demhs', paint: { 'hillshade-exaggeration': orto ? 0.15 : 0.4, 'hillshade-shadow-color': '#5b4f44', 'hillshade-highlight-color': '#ffffff' } });

  // priblíženie podľa veľkosti územia
  const km2 = d.km2 && d.km2 > 0 ? d.km2 : 12;
  const zoom = Math.max(11.2, Math.min(15.2, 14.6 - Math.log2(Math.sqrt(km2) / 2.2)));
  const pohyb = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  const map = new maplibregl.Map({
    container: mapaEl, style, center: [lon, lat], zoom: zoom - 1.6, pitch: pohyb ? 0 : 55, bearing: 0, maxPitch: 78,
    attributionControl: { compact: true }, cooperativeGestures: false,
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
  await new Promise<void>((ok) => map.once('load', () => ok()));
  map.setTerrain({ source: 'dem', exaggeration: 1.5 });
  try { map.setSky?.({ 'sky-color': '#9cc3e8', 'horizon-color': '#dfe9f2', 'fog-color': '#e8eef4', 'sky-horizon-blend': 0.6, 'horizon-fog-blend': 0.5, 'fog-ground-blend': 0.3 }); } catch { /* staršie verzie */ }
  zdroj.hidden = false;
  zdroj.textContent = `${orto ? 'Podklad: ortofotomozaika SR © GKÚ Bratislava, ÚGKK SR (CC BY 4.0)' : 'Podklad: OpenFreeMap, © OpenMapTiles, údaje © prispievatelia OpenStreetMap'}; terén: Terrain Tiles (Mapzen, AWS Open Data). Body záujmu: OpenStreetMap. Mapou môžete kedykoľvek pohnúť sami.`;
  await sTimeoutom(new Promise<void>((ok) => map.once('idle', () => ok())), 8000).catch(() => {});

  // body záujmu v okolí stredu (pomenované, podľa dôležitosti, aspoň 250 m od seba)
  const polomer = Math.max(0.8, Math.min(4, Math.sqrt(km2 / Math.PI) * 0.9));
  const kmOd = (a: [number, number], b: [number, number]) => Math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * Math.cos((a[1] * Math.PI) / 180));
  const body: { n: string; t: string; p: [number, number] }[] = [];
  try {
    const f = map.querySourceFeatures('openmaptiles', { sourceLayer: 'poi' }) as any[];
    const kand = f.map((x) => ({ n: x.properties['name:sk'] || x.properties.name, c: x.properties.class, p: x.geometry?.coordinates as [number, number] }))
      .filter((x) => x.n && TRIEDY[x.c] && Array.isArray(x.p) && typeof x.p[0] === 'number' && kmOd(x.p, [lon, lat]) <= polomer)
      .sort((a, b) => PORADIE.indexOf(a.c) - PORADIE.indexOf(b.c));
    for (const k of kand) if (!body.some((b) => b.n === k.n || kmOd(b.p, k.p) < 0.25) && body.length < 4) body.push({ n: k.n, t: TRIEDY[k.c], p: k.p });
  } catch { /* bez bodov záujmu */ }

  if (!pohyb) { titulok(d.nazov, d.titulky[0]?.[1] ?? ''); tlPauza.hidden = true; return; }

  // scenár preletu: kroky sa dajú pozastaviť (pauza zastaví kameru a krok sa potom zopakuje)
  let pauza = false;
  let i = 0;
  const pohni = (f: () => void) => new Promise<void>((ok) => { map.once('moveend', () => ok()); f(); });
  const tit_ = (k: number) => d.titulky[k] ?? d.titulky[d.titulky.length - 1] ?? [d.nazov, ''];
  const kroky: (() => Promise<void>)[] = [
    async () => { titulok(...tit_(0)); await pohni(() => map.flyTo({ center: [lon, lat], zoom, pitch: 58, bearing: -20, duration: 6000, essential: true })); },
    async () => { titulok(...tit_(1)); await pohni(() => map.rotateTo(map.getBearing() + 70, { duration: 7000, easing: (x: number) => x })); },
    ...body.map((b, k) => async () => {
      titulok(b.n, `${b.t[0].toUpperCase()}${b.t.slice(1)}${tit_(2 + k)[0] ? ` · ${tit_(2 + k)[0]} ${tit_(2 + k)[1]}` : ''}`);
      await pohni(() => map.flyTo({ center: b.p, zoom: Math.min(17, zoom + 2.2), pitch: 66, bearing: map.getBearing() + 35, duration: 5500, essential: true }));
      await sOkamih(1500);
    }),
    async () => { titulok(...tit_(Math.max(2, 2 + body.length))); await pohni(() => map.flyTo({ center: [lon, lat], zoom: zoom - 0.8, pitch: 50, bearing: map.getBearing() + 40, duration: 6000, essential: true })); },
    async () => { titulok(...tit_(d.titulky.length - 1)); await pohni(() => map.rotateTo(map.getBearing() + 90, { duration: 9000, easing: (x: number) => x })); },
  ];
  const hraj = async () => {
    while (i < kroky.length && !pauza) {
      await kroky[i]();
      if (pauza) return;
      i++;
    }
    if (i >= kroky.length) { titulok(d.nazov, 'Koniec preletu – mapou môžete pohybovať sami.'); tlPauza.textContent = '↺ Znova'; tlPauza.dataset.stav = 'znova'; }
  };
  const zastav = () => { if (pauza) return; pauza = true; map.stop(); tlPauza.textContent = '▶ Pokračovať'; tlPauza.dataset.stav = 'pauza'; };
  tlPauza.addEventListener('click', () => {
    if (tlPauza.dataset.stav === 'znova') { i = 0; }
    else if (!pauza) { zastav(); return; }
    pauza = false; tlPauza.textContent = '⏸ Pauza'; tlPauza.dataset.stav = ''; hraj();
  });
  // keď človek sám pohne mapou, prelet sa zastaví
  for (const ev of ['dragstart', 'wheel', 'touchstart', 'rotatestart', 'pitchstart']) map.on(ev, (e: any) => { if (e.originalEvent) zastav(); });
  el.querySelector('[data-pr="cela"]')?.addEventListener('click', () => { const o = okno as any; (document.fullscreenElement ? document.exitFullscreen() : o.requestFullscreen?.())?.catch?.(() => {}); });
  el.querySelector('[data-pr="zavriet"]')?.addEventListener('click', () => {
    zastav();
    okno.hidden = true;
    const uvod = el.querySelector<HTMLElement>('.pr-uvod')!;
    const s = el.querySelector<HTMLButtonElement>('.pr-start')!;
    uvod.hidden = false;
    s.textContent = '▶ Prelet znova';
    s.onclick = () => { okno.hidden = false; uvod.hidden = true; map.resize(); i = 0; pauza = false; tlPauza.textContent = '⏸ Pauza'; tlPauza.dataset.stav = ''; hraj(); };
  });
  hraj();
}
