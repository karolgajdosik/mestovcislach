// Súťaž miest – týždenný kvíz: súhrn bodov za mesto, za ktoré hráč hrá. Žiadne osobné údaje (ani IP): len
// počet hráčov a súčet bodov za mesto a týždeň. KV väzba SUBOJ (rovnaká ako Súboj miest), kľúč sutaz:<týždeň>.
const MESTA = ['bratislava', 'trnava', 'nitra', 'trencin', 'zilina', 'banska-bystrica', 'presov', 'kosice'];
const OTAZOK = 5;
const json = (stav: number, d: unknown) => new Response(JSON.stringify(d), { status: stav, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });

/** ISO týždeň („2026-W44“) v čase Europe/Bratislava; posun o n týždňov */
export function tyzden(n = 0, d = new Date()): string {
  const den = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Bratislava' }).format(d);
  const t = new Date(`${den}T12:00:00Z`);
  t.setUTCDate(t.getUTCDate() + 7 * n);
  const dw = (t.getUTCDay() + 6) % 7;
  t.setUTCDate(t.getUTCDate() - dw + 3);
  const prvy = new Date(Date.UTC(t.getUTCFullYear(), 0, 4));
  const c = 1 + Math.round(((t.getTime() - prvy.getTime()) / 864e5 - 3 + ((prvy.getUTCDay() + 6) % 7)) / 7);
  return `${t.getUTCFullYear()}-W${String(c).padStart(2, '0')}`;
}

type Tabulka = Record<string, [number, number]>; // mesto → [hráčov, bodov]
const citaj = async (kv: any, t: string) => ((await kv.get(`sutaz:${t}`, 'json')) ?? {}) as Tabulka;

export const onRequestGet = async ({ env }: any) => {
  if (!env.SUBOJ) return json(503, { ok: false });
  const [t, p] = [tyzden(), tyzden(-1)];
  return json(200, { ok: true, tyzden: t, tabulka: await citaj(env.SUBOJ, t), minuly: { tyzden: p, tabulka: await citaj(env.SUBOJ, p) } });
};

export const onRequestPost = async ({ request, env }: any) => {
  if (!env.SUBOJ) return json(503, { ok: false });
  let d: any;
  try { d = await request.json(); } catch { return json(400, { ok: false }); }
  const t = String(d.tyzden ?? ''), mesto = String(d.mesto ?? ''), body = Number(d.body);
  if (t !== tyzden() || !MESTA.includes(mesto) || !Number.isInteger(body) || body < 0 || body > OTAZOK) return json(400, { ok: false });
  const tab = await citaj(env.SUBOJ, t);
  const [h, b] = tab[mesto] ?? [0, 0];
  tab[mesto] = [h + 1, b + body]; // pri súčasných zápisoch sa môže pár výsledkov stratiť – na orientačné poradie stačí
  await env.SUBOJ.put(`sutaz:${t}`, JSON.stringify(tab), { expirationTtl: 120 * 864e2 });
  return json(200, { ok: true, tyzden: t, tabulka: tab });
};
