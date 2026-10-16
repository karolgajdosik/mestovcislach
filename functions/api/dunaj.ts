// Cloudflare Pages Function: aktuálny vodný stav Dunaja v Bratislave (a Moravy v Devínskej Novej Vsi, ?rieka=morava) zo SHMÚ.
// SHMÚ nemá API ani CORS, preto stránku stanice spracujeme tu a vrátime malý JSON (cache 10 min).

const STANICE: Record<string, { id: string; nazov: string }> = {
  dunaj: { id: '5140', nazov: 'Bratislava – Dunaj' },
  morava: { id: '5125', nazov: 'Devínska Nová Ves – Morava' },
  hornad: { id: '8705', nazov: 'Košice – Hornád' },
  torysa: { id: '8780', nazov: 'Prešov – Torysa' },
  hron: { id: '7160', nazov: 'Banská Bystrica – Hron' },
  rajcanka: { id: '6340', nazov: 'Žilina – Rajčanka' },
  trnavka: { id: '5230', nazov: 'Bohdanovce nad Trnavou – Trnávka' },
  nitra: { id: '6730', nazov: 'Nitrianska Streda – Nitra' },
};
const url = (id: string) => `https://www.shmu.sk/sk/?page=1&id=hydro_vod_all&station_id=${id}`;
const CACHE_S = 600;

type Bod = [number, number];

function seria(html: string, nazov: string): Bod[] {
  const m = html.match(new RegExp(`var ${nazov}\\s*=\\s*\\{[^]*?data:\\s*(\\[[^]*?\\]\\])\\s*\\}`));
  if (!m) return [];
  try {
    return JSON.parse(m[1]) as Bod[];
  } catch {
    return [];
  }
}

// Posun časového pásma Europe/Bratislava (ms) v danom okamihu – 1 h v zime, 2 h v lete.
function offsetBratislava(t: number): number {
  const casti = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Bratislava', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(t));
  const g = (k: string) => Number(casti.find((p) => p.type === k)!.value);
  return Date.UTC(g('year'), g('month') - 1, g('day'), g('hour'), g('minute')) - Math.floor(t / 60000) * 60000;
}

export function spracuj(html: string, rieka: keyof typeof STANICE = 'dunaj') {
  const text = html.replace(/<script[^]*?<\/script>/g, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  const spa: Record<string, number> = {};
  for (const m of text.matchAll(/Hranica pre (\d)\. stupeň PA:\s*(\d+)\s*cm/g)) spa[m[1]] = Number(m[2]);
  // Prvý riadok tabuľky meraní: čas (miestny), vodný stav, teplota vody
  const riadok = html.match(/h_datum_cas"\s*>\s*([\d.: ]+?)\s*<\/td>\s*<td headers="h_vodny_stav"\s*>\s*(-?\d+)\s*<\/td>\s*<td headers="h_teplota_vody"\s*>\s*([-\d.,]*)\s*</);
  let merane = seria(html, 'base_serie');
  let predpoved = seria(html, 'forecast_serie');
  if (!merane.length && !riadok) throw new Error('Stránka SHMÚ má neznámy formát');
  // Časy v grafe SHMÚ sú miestny čas zapísaný ako UTC. Posun zistíme z posledného riadku tabuľky
  // (napr. 09:00 v tabuľke = 09:00Z v grafe → posun 2 h v lete) a prepočítame na skutočné UTC.
  const m = riadok?.[1].match(/(\d+)\.(\d+)\.(\d{4}) (\d+):(\d+)/);
  if (m && merane.length) {
    const tabulka = Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4], +m[5]);
    const posledny = merane[merane.length - 1][0];
    const posun = Math.abs(tabulka - posledny) < 6 * 3600e3 ? tabulka - posledny : 0;
    // tabulka a graf majú rovnaký „wall clock“; skutočné UTC = wall clock − offset Bratislavy
    const offset = offsetBratislava(posledny);
    merane = merane.map(([t, v]) => [t + posun - offset, v]);
    predpoved = predpoved.map(([t, v]) => [t + posun - offset, v]);
  }
  const posledny = merane[merane.length - 1];
  // Trend za 3 hodiny podľa legendy SHMÚ (±5 cm = ustálená)
  const pred3h = merane.find(([t]) => t >= posledny[0] - 3 * 3600e3);
  const zmena = posledny && pred3h ? posledny[1] - pred3h[1] : 0;
  // Merané hodnoty stačia po hodinách (menší JSON)
  const hodinove = merane.filter(([t], i) => i === merane.length - 1 || new Date(t).getUTCMinutes() === 0);
  return {
    stanica: STANICE[rieka].nazov,
    cas: posledny?.[0] ?? null,
    stav: posledny?.[1] ?? (riadok ? Number(riadok[2]) : null),
    teplota: riadok && riadok[3] ? Number(riadok[3].replace(',', '.')) : null,
    trend: zmena > 5 ? 'stúpa' : zmena < -5 ? 'klesá' : 'ustálená',
    zmena_3h: zmena,
    spa,
    merane: hodinove,
    predpoved,
    zdroj: { nazov: `SHMÚ – vodomerná stanica ${STANICE[rieka].nazov}`, url: url(STANICE[rieka].id) },
  };
}

export const onRequestGet = async (ctx: any) => {
  const cache = (caches as any).default as Cache;
  const ziadana = new URL(ctx.request.url).searchParams.get('rieka') ?? 'dunaj';
  const rieka = (ziadana in STANICE ? ziadana : 'dunaj') as keyof typeof STANICE;
  const kluc = new Request(new URL(`/api/dunaj?rieka=${rieka}`, ctx.request.url).toString());
  const ulozene = await cache.match(kluc);
  if (ulozene) return ulozene;
  try {
    const r = await fetch(url(STANICE[rieka].id), { headers: { 'User-Agent': 'mestovcislach.sk (github.com/karolgajdosik/mestovcislach)' } });
    if (!r.ok) throw new Error(`SHMÚ HTTP ${r.status}`);
    const html = await r.text();
    const data = spracuj(html, rieka);
    const odpoved = new Response(JSON.stringify(data), {
      headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': `public, max-age=${CACHE_S}` },
    });
    ctx.waitUntil(cache.put(kluc, odpoved.clone()));
    return odpoved;
  } catch (e: any) {
    return new Response(JSON.stringify({ chyba: String(e?.message ?? e) }), {
      status: 502, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
    });
  }
};
