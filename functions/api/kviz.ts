// Anonymné počítadlo kvízov (kvíz mesta, kvíz obce, Súťaž miest): koľko kvízov sa spustilo (prvá odpoveď) a dohralo.
// Ukladajú sa LEN počty za kvíz a mesiac – žiadne IP adresy, identifikátory ani odpovede. Roboty sa nepočítajú
// (kvíz spúšťa až kliknutie na odpoveď; navyše filter User-Agent a pôvodu požiadavky).
// KV väzba SUBOJ (rovnaká ako Súboj miest), kľúč kviz:<RRRR-MM> → { "/trencin/kviz": [spustené, dohrané], … }.
const json = (stav: number, d: unknown, cache = 'no-store') => new Response(JSON.stringify(d), { status: stav, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': cache } });
const mesiac = (posun = 0) => { const d = new Date(); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + posun); return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Bratislava', year: 'numeric', month: '2-digit' }).format(d); };
const PLATNY = /^\/(?:[a-z0-9-]+\/){1,3}kviz$|^\/sutaz$/;
const ROBOT = /bot|crawl|spider|slurp|headless|lighthouse|preview|facebookexternalhit|curl|wget|python|go-http/i;
const MAX_KVIZOV = 4000; // ochrana pred zaplnením KV podvrhnutými adresami (obcí je ~2 900, miest a súťaže pár)

type Tab = Record<string, [number, number]>;

export const onRequestPost = async ({ request, env }: any) => {
  if (!env.SUBOJ) return json(503, { ok: false });
  const ua = request.headers.get('user-agent') ?? '';
  const povod = request.headers.get('origin') ?? request.headers.get('referer') ?? '';
  let host = '';
  try { host = new URL(povod).hostname; } catch { /* bez pôvodu */ }
  if (ROBOT.test(ua) || !(host === 'mestovcislach.sk' || host.endsWith('.mestovcislach.sk') || host.endsWith('.pages.dev'))) return new Response(null, { status: 204 });
  let d: any;
  try { d = JSON.parse(await request.text()); } catch { return json(400, { ok: false }); }
  const udalost = d?.u === 'start' ? 0 : d?.u === 'koniec' ? 1 : -1;
  const kviz = String(d?.k ?? '').replace(/\/+$/, '');
  if (udalost < 0 || !PLATNY.test(kviz) || kviz.length > 120) return json(400, { ok: false });
  const kluc = `kviz:${mesiac()}`;
  const tab = ((await env.SUBOJ.get(kluc, 'json')) ?? {}) as Tab;
  if (!tab[kviz] && Object.keys(tab).length >= MAX_KVIZOV) return new Response(null, { status: 204 });
  const r = tab[kviz] ?? [0, 0];
  r[udalost]++;
  tab[kviz] = r; // pri súčasných zápisoch sa môže pár udalostí stratiť – na orientačné počty stačí
  await env.SUBOJ.put(kluc, JSON.stringify(tab), { expirationTtl: 800 * 864e2 });
  return new Response(null, { status: 204 });
};

/** Súhrn za posledné mesiace: spolu a najhrávanejšie kvízy (verejné – len počty). ?mesiace=1..12 */
export const onRequestGet = async ({ request, env }: any) => {
  if (!env.SUBOJ) return json(503, { ok: false });
  const n = Math.min(12, Math.max(1, Number(new URL(request.url).searchParams.get('mesiace')) || 3));
  const out: Record<string, { spustene: number; dohrane: number; kvizov: number; top: [string, number, number][] }> = {};
  for (let i = 0; i > -n; i--) {
    const m = mesiac(i);
    const tab = ((await env.SUBOJ.get(`kviz:${m}`, 'json')) ?? {}) as Tab;
    const r = Object.entries(tab).filter(([k]) => !k.startsWith('/test')); // /test/kviz = overenie počítadla, nezobrazuje sa
    out[m] = {
      spustene: r.reduce((s, [, [a]]) => s + a, 0),
      dohrane: r.reduce((s, [, [, b]]) => s + b, 0),
      kvizov: r.length,
      top: r.sort((a, b) => b[1][0] - a[1][0]).slice(0, 15).map(([k, [a, b]]) => [k, a, b]),
    };
  }
  return json(200, { ok: true, mesiace: out }, 'public, max-age=300');
};
