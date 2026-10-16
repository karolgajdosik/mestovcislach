// Cloudflare Pages Function: aktuálna kvalita ovzdušia v Bratislave zo staníc SHMÚ (index kvality ovzdušia IKO).
// SHMÚ API nemá CORS, preto ho voláme tu a vraciame len bratislavské stanice (cache 10 min).

import MESTA from '../../src/mesta.json';

const API = 'https://www.shmu.sk/api/v1/airquality/';
const CACHE_S = 600;

// Legenda SHMÚ: dobrá 0–33, zhoršená > 33–66, zlá > 66–100, veľmi zlá > 100
export function kategoria(iko: number | null | undefined) {
  if (iko == null) return null;
  if (iko <= 33) return { stupen: 1, nazov: 'dobrá' };
  if (iko <= 66) return { stupen: 2, nazov: 'zhoršená' };
  if (iko <= 100) return { stupen: 3, nazov: 'zlá' };
  return { stupen: 4, nazov: 'veľmi zlá' };
}

const LATKY = ['pm10', 'pm25', 'no2', 'o3', 'so2'] as const;

export function spracuj(stanice: any[], iko: any[], teraz = Date.now(), mesto = 'Bratislava') {
  const ba = new Map<number, any>((stanice ?? []).filter((s) => String(s.station_name ?? '').startsWith(mesto + ',')).map((s) => [s.station_id, s]));
  const vysledok: any[] = [];
  for (const z of iko ?? []) {
    const st = ba.get(z.station_id);
    if (!st) continue;
    const data = [...(z.data ?? [])].filter((d) => d.iko_v != null).sort((a, b) => a.dt_ts - b.dt_ts);
    const posl = data[data.length - 1];
    if (!posl) continue;
    vysledok.push({
      id: st.station_id,
      nazov: st.station_name.slice(mesto.length + 1).trim().replace('Pod. Biskupice', 'Podunajské Biskupice'),
      lat: st.gps_lat, lon: st.gps_lon,
      cas: posl.dt_ts * 1000,
      iko: posl.iko_v,
      kategoria: kategoria(posl.iko_v),
      latky: Object.fromEntries(LATKY.filter((l) => posl[l + '_v'] != null).map((l) => [l, posl[l + '_v']])),
      rad: data.slice(-24).map((d) => [d.dt_ts * 1000, d.iko_v]),
    });
  }
  vysledok.sort((a, b) => a.nazov.localeCompare(b.nazov, 'sk'));
  // Mesto: najhoršia stanica z meraní za posledné 3 hodiny
  const aktualne = vysledok.filter((s) => teraz - s.cas < 3 * 3600e3);
  const najhorsia = aktualne.reduce((a: any, s: any) => (!a || s.iko > a.iko ? s : a), null);
  return {
    mesto: najhorsia ? { iko: najhorsia.iko, kategoria: najhorsia.kategoria, stanica: najhorsia.nazov, cas: najhorsia.cas, stanic: aktualne.length } : null,
    stanice: vysledok,
    legenda: 'IKO podľa SHMÚ: dobrá 0–33, zhoršená 34–66, zlá 67–100, veľmi zlá nad 100',
    zdroj: { nazov: 'SHMÚ – index kvality ovzdušia', url: 'https://www.shmu.sk/sk/?page=1&id=oko_iko' },
  };
}

export const onRequestGet = async (ctx: any) => {
  const cache = (caches as any).default as Cache;
  const slug = new URL(ctx.request.url).searchParams.get('mesto') ?? 'bratislava';
  const mesto = (MESTA as any[]).find((m) => m.slug === slug)?.nazov ?? 'Bratislava';
  const kluc = new Request(new URL(`/api/ovzdusie?mesto=${slug}`, ctx.request.url).toString());
  const ulozene = await cache.match(kluc);
  if (ulozene) return ulozene;
  try {
    const hl = { headers: { 'User-Agent': 'mestovcislach.sk (github.com/karolgajdosik/mestovcislach)' } };
    const [s, i] = await Promise.all([fetch(API + 'getstations', hl), fetch(API + 'getikodata2?history=24', hl)]);
    if (!s.ok || !i.ok) throw new Error(`SHMÚ HTTP ${s.status}/${i.status}`);
    const data = spracuj(await s.json(), await i.json(), Date.now(), mesto);
    if (!data.stanice.length) throw new Error(`SHMÚ nevrátil stanice pre mesto ${mesto}`);
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
