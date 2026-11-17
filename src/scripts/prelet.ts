// 3D prelet nad obcou / mestskou časťou (MapLibre GL, načíta sa až po kliknutí).
// Podklad: vektorová mapa OpenFreeMap (ulice, názvy, 3D budovy); tlačidlom sa dá prepnúť na leteckú snímku – ortofotomozaika SR
// (GKÚ Bratislava, CC BY 4.0), vložená pod cesty a názvy, ak služba odpovie a povolí CORS.
// Terén: Terrain Tiles (Terrarium, AWS Open Data). Zastávky kamery: pomenované body záujmu z dlaždíc OpenMapTiles v okolí.

type Pamiatka = { n: string; p: [number, number]; t: string; q: string; f?: { u: string; a: string; l: string; s: string }; w?: string };
type Data = { nazov: string; stred: [number, number]; bbox?: [number, number, number, number] | null; km2?: number | null; titulky: [string, string][]; pamiatky?: Pamiatka[] };

// ---------- hovorené slovo: slovenský hlas zabudovaný v prehliadači / systéme (Web Speech API, zadarmo, nič sa nesťahuje) ----------
const reč = typeof window !== 'undefined' && 'speechSynthesis' in window ? window.speechSynthesis : null;
function slovenskyHlas(): Promise<SpeechSynthesisVoice | null> {
  if (!reč) return Promise.resolve(null);
  const vyber = () => { const v = reč.getVoices(); return v.find((x) => /^sk([-_]|$)/i.test(x.lang) && /enhanced|premium|natural|neural/i.test(x.name)) ?? v.find((x) => /^sk([-_]|$)/i.test(x.lang)) ?? null; };
  const hned = vyber();
  if (hned || reč.getVoices().length) return Promise.resolve(hned);
  return new Promise((ok) => { const t = setTimeout(() => ok(vyber()), 1500); reč.addEventListener('voiceschanged', () => { clearTimeout(t); ok(vyber()); }, { once: true }); });
}

const OFM = 'https://tiles.openfreemap.org';
const WMS = 'https://zbgisws.skgeodesy.sk/zbgis_ortofoto_wms/service.svc/get';
const EOX = 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg';
const AGS = 'https://zbgis.skgeodesy.sk/zbgis/rest/services/Ortofoto/MapServer';
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

/** Je obrázok skutočná snímka? Prázdna dlaždica („bez dát“) je jednofarebná – posudzuje sa rozptyl jasu. */
async function nieJePrazdny(blob: Blob): Promise<boolean> {
  try {
    const bmp = await createImageBitmap(blob);
    const c = document.createElement('canvas');
    c.width = 32; c.height = 32;
    const g = c.getContext('2d')!;
    g.drawImage(bmp, 0, 0, 32, 32);
    const d = g.getImageData(0, 0, 32, 32).data;
    let s = 0, s2 = 0, n = 0;
    for (let k = 0; k < d.length; k += 4) { if (d[k + 3] < 10) continue; const j = 0.3 * d[k] + 0.59 * d[k + 1] + 0.11 * d[k + 2]; s += j; s2 += j * j; n++; }
    if (n < 100) return false;
    const pr = s / n;
    return Math.sqrt(Math.max(0, s2 / n - pr * pr)) > 6 && pr < 245;
  } catch {
    return false;
  }
}

/** Ortofoto ZBGIS: skúsi viac spôsobov (ArcGIS REST export, WMS po jednotlivých vrstvách) a vráti šablónu dlaždíc,
 *  pri ktorej skúšobná dlaždica okolo obce prejde cez CORS a nie je prázdna. Služby GKÚ sú dostupné len zo Slovenska. */
async function ortofoto(lat: number, lon: number): Promise<{ sablona: string; popis: string } | null> {
  const x = (lon * 20037508.34) / 180, y = (Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / 180)) * (20037508.34 / 180);
  const skus = async (sablona: string): Promise<boolean> => {
    try {
      const r = await sTimeoutom(fetch(sablona.replace('{bbox-epsg-3857}', `${x - 400},${y - 400},${x + 400},${y + 400}`), { mode: 'cors' }), 7000);
      if (!r.ok || !(r.headers.get('content-type') ?? '').startsWith('image/')) return false;
      return nieJePrazdny(await r.blob());
    } catch {
      return false;
    }
  };
  const kandidati: { sablona: string; popis: string }[] = [
    { sablona: `${AGS}/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=512,512&format=jpg&transparent=false&f=image`, popis: 'ArcGIS REST' },
  ];
  try {
    const cap = await sTimeoutom(fetch(`${WMS}?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0`, { mode: 'cors' }).then((r) => (r.ok ? r.text() : Promise.reject())), 6000);
    const doc = new DOMParser().parseFromString(cap, 'text/xml');
    const mena = [...new Set([...doc.getElementsByTagName('Name')].filter((n) => n.parentElement?.tagName === 'Layer').map((n) => n.textContent?.trim()).filter(Boolean) as string[])];
    for (const v of mena.slice(0, 8)) kandidati.push({ sablona: `${WMS}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=${encodeURIComponent(v)}&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=512&HEIGHT=512&FORMAT=image/jpeg`, popis: `WMS ${v}` });
    if (mena.length) kandidati.push({ sablona: `${WMS}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=${encodeURIComponent(mena.join(','))}&STYLES=&SRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=512&HEIGHT=512&FORMAT=image/jpeg`, popis: 'WMS 1.1.1' });
  } catch { /* WMS nedostupné – ostáva ArcGIS REST */ }
  for (const k of kandidati) if (await skus(k.sablona)) return k;
  return null;
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
  el.classList.add('pr-otvoreny');
  const fotoEl = tit.querySelector<HTMLImageElement>('.pr-foto');
  const kreditEl = tit.querySelector<HTMLElement>('.pr-kredit');
  const titulok = (b: string, s = '', f?: Pamiatka['f']) => {
    tit.querySelector('b')!.textContent = b; tit.querySelector('span')!.textContent = s; tit.classList.toggle('pr-skryty', !b);
    if (fotoEl) { fotoEl.hidden = !f; if (f) { fotoEl.src = f.u; fotoEl.alt = b; } else fotoEl.removeAttribute('src'); }
    if (kreditEl) { kreditEl.hidden = !f; kreditEl.textContent = f ? `Foto: ${f.a || 'Wikimedia Commons'}${f.l ? ` (${f.l})` : ''}` : ''; }
    tit.classList.toggle('pr-s-fotkou', !!f);
  };
  titulok('Načítavam mapu…');

  const [lat, lon] = d.stred;
  const [mod, worker] = await Promise.all([
    import('maplibre-gl/dist/maplibre-gl-csp.js' as string),
    import('maplibre-gl/dist/maplibre-gl-csp-worker.js?url' as string).then((m) => m.default as string),
    // štýly MapLibre ako samostatný súbor až pri spustení (inak by Astro pridalo 70 kB CSS do hlavičky každej obce)
    import('maplibre-gl/dist/maplibre-gl.css?url' as string).then((m) => new Promise<void>((ok) => {
      const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = m.default; l.onload = () => ok(); l.onerror = () => ok(); document.head.append(l);
    })),
  ]);
  const maplibregl: any = mod.default ?? mod;
  maplibregl.setWorkerUrl(worker);

  // štýl: vždy plná mapa (ulice, názvy, 3D budovy – OpenFreeMap); letecká snímka sa pridá tlačidlom pod cesty a názvy
  const style: any = await fetch(`${OFM}/styles/liberty`).then((r) => r.json());
  style.sources.dem = { type: 'raster-dem', tiles: [DEM], tileSize: 256, encoding: 'terrarium', maxzoom: 14, attribution: 'Terén: Terrain Tiles (Mapzen, AWS Open Data)' };
  // tieňovaný reliéf (samostatný zdroj – MapLibre odporúča nezdieľať zdroj terénu a tieňovania)
  style.sources.demhs = { type: 'raster-dem', tiles: [DEM], tileSize: 256, encoding: 'terrarium', maxzoom: 14 };
  const prvaCiara = style.layers.findIndex((l: any) => l.type === 'line' || l.type === 'symbol' || l.type === 'fill-extrusion');
  style.layers.splice(Math.max(1, prvaCiara), 0, { id: 'relief', type: 'hillshade', source: 'demhs', paint: { 'hillshade-exaggeration': 0.4, 'hillshade-shadow-color': '#5b4f44', 'hillshade-highlight-color': '#ffffff' } });

  // priblíženie podľa veľkosti územia
  const km2 = d.km2 && d.km2 > 0 ? d.km2 : 12;
  const zoom = Math.max(12, Math.min(15.4, 15.4 - Math.log2(Math.sqrt(km2) / 2.2)));
  const pohyb = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  const map = new maplibregl.Map({
    container: mapaEl, style, center: [lon, lat], zoom: zoom - 1.6, pitch: pohyb ? 0 : 55, bearing: 0, maxPitch: 78,
    attributionControl: false, cooperativeGestures: false,
  });
  // celá obrazovka: Fullscreen API (aj s predponou webkit); kde nie je (iPhone) alebo zlyhá, okno sa roztiahne cez celé okno prehliadača
  const tlCela = el.querySelector<HTMLButtonElement>('[data-pr="cela"]');
  const o: any = okno;
  const jeCela = () => !!(document.fullscreenElement || (document as any).webkitFullscreenElement) || okno.classList.contains('pr-max');
  const stavCela = () => { if (tlCela) { tlCela.textContent = jeCela() ? '✕⛶' : '⛶'; tlCela.setAttribute('aria-label', jeCela() ? 'Zmenšiť' : 'Na celú obrazovku'); } setTimeout(() => map.resize(), 60); };
  const maxOkno = (zap: boolean) => { okno.classList.toggle('pr-max', zap); document.documentElement.classList.toggle('pr-max-otvorene', zap); stavCela(); };
  tlCela?.addEventListener('click', async () => {
    if (okno.classList.contains('pr-max')) { maxOkno(false); return; }
    if (document.fullscreenElement || (document as any).webkitFullscreenElement) { (document.exitFullscreen?.() ?? (document as any).webkitExitFullscreen?.()); return; }
    const poziadaj = o.requestFullscreen ?? o.webkitRequestFullscreen;
    if (!poziadaj) { maxOkno(true); return; }
    try { await poziadaj.call(o); } catch { maxOkno(true); }
  });
  document.addEventListener('fullscreenchange', stavCela);
  document.addEventListener('webkitfullscreenchange', stavCela);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && okno.classList.contains('pr-max')) maxOkno(false); });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
  map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
  await new Promise<void>((ok) => map.once('load', () => ok()));
  map.setTerrain({ source: 'dem', exaggeration: 1.5 });
  // zbalené autorstvo (ikona „i“) – celé zdroje sú pod mapou
  mapaEl.querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show');
  try { map.setSky?.({ 'sky-color': '#9cc3e8', 'horizon-color': '#dfe9f2', 'fog-color': '#e8eef4', 'sky-horizon-blend': 0.6, 'horizon-fog-blend': 0.5, 'fog-ground-blend': 0.3 }); } catch { /* staršie verzie */ }
  zdroj.hidden = false;
  const ZDROJ_MAPA = 'Mapa: OpenFreeMap, © OpenMapTiles, údaje © prispievatelia OpenStreetMap; terén: Terrain Tiles (Mapzen, AWS Open Data). Mapou môžete kedykoľvek pohnúť sami.';
  zdroj.textContent = ZDROJ_MAPA;
  // prepínač Mapa / Letecká snímka: ortofoto ZBGIS sa vloží pod cesty, budovy a názvy (hybridná mapa)
  const tlPodklad = el.querySelector<HTMLButtonElement>('[data-pr="podklad"]');
  let letecka = false;
  let plosne: string[] = [];
  let chybaOrto = false;
  let zdrojOrto = '';
  tlPodklad?.addEventListener('click', async () => {
    if (!map.getLayer('orto')) {
      tlPodklad.disabled = true;
      tlPodklad.textContent = 'Načítavam snímky…';
      const najdene = await ortofoto(lat, lon);
      tlPodklad.disabled = false;
      if (najdene) {
        zdrojOrto = `Letecká snímka: ortofotomozaika SR © GKÚ Bratislava, ÚGKK SR (CC BY 4.0; ${najdene.popis})`;
        map.addSource('orto', { type: 'raster', tiles: [najdene.sablona], tileSize: 512, maxzoom: 19, attribution: 'Ortofotomozaika SR © GKÚ Bratislava, ÚGKK SR (CC BY 4.0)' });
      } else {
        // náhrada mimo dosahu služieb GKÚ: satelitná mozaika Sentinel-2 (10 m, CC BY 4.0) – farebná, ale menej podrobná
        zdrojOrto = 'Satelitná snímka: Sentinel-2 cloudless 2016 © EOX IT Services GmbH, obsahuje upravené dáta Copernicus Sentinel (CC BY 4.0) – letecké snímky GKÚ sa nepodarilo načítať';
        map.addSource('orto', { type: 'raster', tiles: [EOX], tileSize: 256, maxzoom: 15, attribution: 'Sentinel-2 cloudless 2016 © EOX (CC BY 4.0)' });
      }
      // snímka hneď nad pozadie; plošné vrstvy mapy (zástavba, lesy, voda, parky) sa pri leteckej snímke skryjú,
      // inak by ju prekryli – ostanú cesty, 3D budovy a názvy
      const vrstvy = map.getStyle().layers as any[];
      const nad = vrstvy.find((l) => l.type !== 'background')?.id;
      map.addLayer({ id: 'orto', type: 'raster', source: 'orto', layout: { visibility: 'none' } }, nad);
      plosne = vrstvy.filter((l) => l.type === 'fill' || l.type === 'hillshade' || (l.type === 'raster' && l.id !== 'orto') || (l.type === 'line' && /park|landuse|landcover|wood|grass|farm|natural|aeroway|pitch|area/i.test(`${l.id} ${l['source-layer'] ?? ''}`))).map((l) => l.id);
      map.on('error', (e: any) => { if (e.sourceId === 'orto' && !chybaOrto) { chybaOrto = true; zdroj.textContent = 'Časť leteckých snímok sa nepodarilo načítať (server neodpovedá). ' + ZDROJ_MAPA; } });
    }
    letecka = !letecka;
    map.setLayoutProperty('orto', 'visibility', letecka ? 'visible' : 'none');
    for (const id of plosne) map.setLayoutProperty(id, 'visibility', letecka ? 'none' : 'visible');
    tlPodklad.textContent = letecka ? '🗺 Mapa' : '🛰 Letecká snímka';
    zdroj.textContent = letecka ? `${zdrojOrto}. ${ZDROJ_MAPA}` : ZDROJ_MAPA;
  });
  await sTimeoutom(new Promise<void>((ok) => map.once('idle', () => ok())), 8000).catch(() => {});

  // body záujmu v okolí stredu (pomenované, podľa dôležitosti, aspoň 250 m od seba) – hľadajú sa až po nálete,
  // pri malom priblížení dlaždice OpenMapTiles body záujmu ešte neobsahujú
  const polomer = Math.max(0.8, Math.min(4, Math.sqrt(km2 / Math.PI) * 0.9));
  const kmOd = (a: [number, number], b: [number, number]) => Math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * Math.cos((a[1] * Math.PI) / 180));
  const najdiBody = () => {
    const body: { n: string; t: string; p: [number, number] }[] = [];
    try {
      const f = map.querySourceFeatures('openmaptiles', { sourceLayer: 'poi' }) as any[];
      const kand = f.map((x) => ({ n: x.properties['name:sk'] || x.properties.name, c: x.properties.class, p: x.geometry?.coordinates as [number, number] }))
        .filter((x) => x.n && TRIEDY[x.c] && Array.isArray(x.p) && typeof x.p[0] === 'number' && kmOd(x.p, [lon, lat]) <= polomer)
        .sort((a, b) => PORADIE.indexOf(a.c) - PORADIE.indexOf(b.c));
      // najviac 2 miesta jedného druhu, aby prelet nebol len o kostoloch
      for (const k of kand) if (!body.some((b) => b.n === k.n || kmOd(b.p, k.p) < 0.25) && body.filter((b) => b.t === TRIEDY[k.c]).length < 2 && body.length < 4) body.push({ n: k.n, t: TRIEDY[k.c], p: k.p });
    } catch { /* bez bodov záujmu */ }
    return body;
  };
  (el as any).__mapa = map;

  if (!pohyb) { titulok(d.nazov, d.titulky[0]?.[1] ?? ''); tlPauza.hidden = true; return; }

  const hlas = await slovenskyHlas();
  const tlHlas = el.querySelector<HTMLButtonElement>('[data-pr="hlas"]');
  let hovor = !!hlas;
  if (tlHlas) {
    tlHlas.hidden = !hlas;
    const stavHlasu = () => { tlHlas.textContent = hovor ? '🔊 Hlas' : '🔇 Bez hlasu'; tlHlas.setAttribute('aria-pressed', String(hovor)); };
    tlHlas.addEventListener('click', () => { hovor = !hovor; if (!hovor) reč?.cancel(); stavHlasu(); });
    stavHlasu();
  }
  if (!hlas) zdroj.textContent += ' Prehliadač nemá slovenský hlas – prelet je s titulkami bez zvuku.';
  /** Prečíta text a počká na koniec (pri vypnutom hlase približný čas čítania titulku). */
  let prerusReč: (() => void) | null = null;
  const povedz = (text: string, minMs = 0) => new Promise<void>((ok) => {
    const odhad = Math.max(minMs, Math.min(16000, 2500 + text.length * 55));
    if (!hovor || !hlas || !reč || !text) { const t = setTimeout(ok, odhad); prerusReč = () => { clearTimeout(t); ok(); }; return; }
    reč.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.voice = hlas; u.lang = hlas.lang; u.rate = 1; u.pitch = 1;
    let hotovo = false;
    const koniec = () => { if (!hotovo) { hotovo = true; ok(); } };
    prerusReč = koniec;
    u.onend = koniec; u.onerror = koniec;
    setTimeout(koniec, 3000 + text.length * 110); // poistka, ak prehliadač „zabudne“ ohlásiť koniec
    reč.speak(u);
  });
  const reci = (b: string, s: string) => `${b}. ${s}`.replace(/\s+/g, ' ').replace(/−/g, 'mínus ').replace(/\+(\d)/g, 'plus $1').replace(/ m n\. m\./g, ' metrov nad morom');

  // scenár preletu: kroky sa dajú pozastaviť (pauza zastaví kameru a krok sa potom zopakuje)
  let pauza = false;
  let i = 0;
  let pocetBodov = 0;
  const pohni = (f: () => void) => new Promise<void>((ok) => { map.once('moveend', () => ok()); f(); });
  const tit_ = (k: number) => d.titulky[k] ?? d.titulky[d.titulky.length - 1] ?? [d.nazov, ''];
  const kroky: (() => Promise<void>)[] = [
    async () => { titulok(...tit_(0)); await Promise.all([pohni(() => map.flyTo({ center: [lon, lat], zoom, pitch: 58, bearing: -20, duration: 6000, essential: true })), povedz(reci(...tit_(0)))]); },
    async () => { titulok(...tit_(1)); await Promise.all([pohni(() => map.rotateTo(map.getBearing() + 70, { duration: 7000, easing: (x: number) => x, essential: true })), povedz(reci(...tit_(1)))]); },
    ...(d.pamiatky ?? []).map((pm) => async () => {
      // významná pamiatka: prílet, titulok s fotkou a pomalé obletenie počas čítania
      const meno = pm.n.replace(/\s*\([^()]*\)$/, ''); // „Kostol … (Košice)“ → bez rozlišovacej zátvorky
      titulok(meno, pm.t, pm.f);
      await pohni(() => map.flyTo({ center: [pm.p[1], pm.p[0]], zoom: 17, pitch: 62, bearing: map.getBearing() + 40, duration: 5000, essential: true }));
      if (pauza) return;
      const citanie = povedz(reci(meno, pm.t), 6000);
      let obieha = true;
      // každé kolo trvá aspoň chvíľu (aj keď prehliadač pohyb preskočí – napr. obmedzené animácie), inak by slučka zablokovala stránku
      const krut = async () => { while (obieha && !pauza) await Promise.all([pohni(() => map.rotateTo(map.getBearing() + 25, { duration: 4000, easing: (x: number) => x, essential: true })), sOkamih(500)]); };
      const k = krut();
      await citanie;
      obieha = false;
      await k;
    }),
    async () => {
      if ((d.pamiatky ?? []).length) return; // pamiatky z Wikidata nahrádzajú body z mapy
      // zastávky pri významných miestach (pri pauze sa krok zopakuje od začiatku)
      let body = najdiBody();
      if (!body.length && map.getZoom() < 14.6) {
        // body záujmu sú v dlaždiciach až pri väčšom priblížení – priblížiť a skúsiť znova
        await pohni(() => map.easeTo({ zoom: 14.8, pitch: 62, duration: 3000, essential: true }));
        await sTimeoutom(new Promise<void>((ok) => map.once('idle', () => ok())), 6000).catch(() => {});
        body = najdiBody();
      }
      pocetBodov = body.length;
      for (const [k, b] of body.entries()) {
        if (pauza) return;
        const [ta, tb] = 2 + k < d.titulky.length - 1 ? tit_(2 + k) : ['', ''];
        titulok(b.n, `${b.t[0].toUpperCase()}${b.t.slice(1)}${ta ? ` · ${ta}${tb ? ` – ${tb}` : ''}` : ''}`);
        await Promise.all([pohni(() => map.flyTo({ center: b.p, zoom: Math.min(17, zoom + 2.2), pitch: 66, bearing: map.getBearing() + 35, duration: 5500, essential: true })), povedz(ta ? reci(b.n, `${ta}, ${tb}`) : b.n)]);
        await sOkamih(800);
      }
    },
    async () => { const tt = 2 + pocetBodov < d.titulky.length - 1 ? tit_(2 + pocetBodov) : tit_(0); titulok(...tt); await Promise.all([pohni(() => map.flyTo({ center: [lon, lat], zoom: zoom - 0.8, pitch: 50, bearing: map.getBearing() + 40, duration: 6000, essential: true })), povedz(reci(...tt))]); },
    async () => { titulok(...tit_(d.titulky.length - 1)); await Promise.all([pohni(() => map.rotateTo(map.getBearing() + 90, { duration: 9000, easing: (x: number) => x, essential: true })), povedz(`${d.nazov}. Ďalšie čísla nájdete na stránke mesto v číslach.`)]); },
  ];
  // kapitoly: zoznam zastávok pod mapou a tlačidlá ⏮ ⏭ – dá sa preskočiť dopredu aj vrátiť
  const pam = d.pamiatky ?? [];
  const kapitoly: { krok: number; nazov: string; foto?: string }[] = [
    { krok: 0, nazov: d.nazov },
    { krok: 1, nazov: tit_(1)[0] },
    ...pam.map((pm, k) => ({ krok: 2 + k, nazov: pm.n.replace(/\s*\([^()]*\)$/, ''), foto: pm.f?.u })),
    ...(pam.length ? [] : [{ krok: 2, nazov: 'Zaujímavé miesta' }]),
    { krok: kroky.length - 2, nazov: 'Odlet' },
    { krok: kroky.length - 1, nazov: 'Záver' },
  ];
  const zoznam = el.querySelector<HTMLOListElement>('.pr-kapitoly');
  const tlSpat = el.querySelector<HTMLButtonElement>('[data-pr="spat"]');
  const tlDalej = el.querySelector<HTMLButtonElement>('[data-pr="dalej"]');
  const kapitolaKroku = (k: number) => { let x = 0; kapitoly.forEach((kp, j) => { if (kp.krok <= k) x = j; }); return x; };
  const oznac = () => {
    const a = kapitolaKroku(Math.min(i, kroky.length - 1));
    zoznam?.querySelectorAll('button').forEach((b, j) => { b.classList.toggle('pr-akt', j === a); if (j === a) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
    zoznam?.querySelector<HTMLElement>('.pr-akt')?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    if (tlSpat) tlSpat.disabled = a === 0;
    if (tlDalej) tlDalej.disabled = a >= kapitoly.length - 1;
  };
  if (zoznam) {
    zoznam.replaceChildren(...kapitoly.map((kp, j) => {
      const li = document.createElement('li');
      const b = document.createElement('button');
      b.type = 'button';
      if (kp.foto) { const im = document.createElement('img'); im.src = kp.foto; im.alt = ''; im.loading = 'lazy'; im.referrerPolicy = 'no-referrer'; b.append(im); }
      const s = document.createElement('span'); s.textContent = `${j + 1}. ${kp.nazov}`; b.append(s);
      b.addEventListener('click', () => skoc(kp.krok));
      li.append(b); return li;
    }));
    zoznam.hidden = false;
  }

  let beh: Promise<void> | null = null;
  const hraj = async () => {
    while (i < kroky.length && !pauza) {
      oznac();
      await kroky[i]();
      if (pauza) return;
      i++;
    }
    if (i >= kroky.length) { titulok(d.nazov, 'Koniec preletu – mapou môžete pohybovať sami.'); tlPauza.textContent = '↺ Znova'; tlPauza.dataset.stav = 'znova'; oznac(); }
  };
  const spusti = () => { pauza = false; tlPauza.textContent = '⏸ Pauza'; tlPauza.dataset.stav = ''; beh = hraj(); };
  const zastav = () => { if (pauza) return; pauza = true; map.stop(); reč?.cancel(); prerusReč?.(); tlPauza.textContent = '▶ Pokračovať'; tlPauza.dataset.stav = 'pauza'; };
  /** Preskočí na krok (zastávku) – bežiaci krok sa preruší a prelet pokračuje odtiaľ. */
  const skoc = async (k: number) => {
    zastav();
    await beh?.catch(() => {});
    i = Math.max(0, Math.min(kroky.length - 1, k));
    if (i > 2 && !pam.length) pocetBodov = 0;
    spusti();
  };
  tlSpat?.addEventListener('click', () => { const a = kapitolaKroku(Math.min(i, kroky.length - 1)); skoc(kapitoly[Math.max(0, a - 1)].krok); });
  tlDalej?.addEventListener('click', () => { const a = kapitolaKroku(Math.min(i, kroky.length - 1)); skoc(kapitoly[Math.min(kapitoly.length - 1, a + 1)].krok); });
  tlPauza.addEventListener('click', () => {
    if (tlPauza.dataset.stav === 'znova') { i = 0; }
    else if (!pauza) { zastav(); return; }
    spusti();
  });
  // keď človek sám pohne mapou, prelet sa zastaví
  for (const ev of ['dragstart', 'wheel', 'touchstart', 'rotatestart', 'pitchstart']) map.on(ev, (e: any) => { if (e.originalEvent) zastav(); });
  el.querySelector('[data-pr="zavriet"]')?.addEventListener('click', () => {
    zastav();
    if (okno.classList.contains('pr-max')) maxOkno(false);
    if (document.fullscreenElement) document.exitFullscreen?.();
    okno.hidden = true;
    if (zoznam) zoznam.hidden = true;
    const uvod = el.querySelector<HTMLElement>('.pr-uvod')!;
    const s = el.querySelector<HTMLButtonElement>('.pr-start')!;
    uvod.hidden = false;
    el.classList.remove('pr-otvoreny');
    s.textContent = '▶ Prelet znova';
    s.onclick = () => { okno.hidden = false; uvod.hidden = true; el.classList.add('pr-otvoreny'); if (zoznam) zoznam.hidden = false; map.resize(); i = 0; spusti(); };
  });
  spusti();
}
