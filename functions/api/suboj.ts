// Súboj miest – súhrn odpovedí na dennú otázku (koľko ľudí tipovalo ktoré mesto). Žiadne osobné údaje: len počty.
// Vyžaduje KV väzbu SUBOJ (Cloudflare Pages → Settings → Bindings → KV namespace „SUBOJ“); bez nej vráti 503
// a stránka súhrn len nezobrazí.
const MESTA = ['bratislava', 'trnava', 'nitra', 'trencin', 'zilina', 'banska-bystrica', 'presov', 'kosice'];
const json = (stav: number, d: unknown) => new Response(JSON.stringify(d), { status: stav, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });
const dnes = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Bratislava' }).format(new Date());
const platnyDen = (d: string) => /^\d{4}-\d{2}-\d{2}$/.test(d) && Math.abs(Date.parse(d) - Date.parse(dnes())) <= 864e5;

async function pocty(kv: any, den: string) {
  const v = await kv.get(`suboj:${den}`, 'json');
  return (v ?? {}) as Record<string, number>;
}

export const onRequestGet = async ({ request, env }: any) => {
  if (!env.SUBOJ) return json(503, { ok: false });
  const den = new URL(request.url).searchParams.get('den') ?? '';
  if (!platnyDen(den)) return json(400, { ok: false });
  return json(200, { ok: true, pocty: await pocty(env.SUBOJ, den) });
};

export const onRequestPost = async ({ request, env }: any) => {
  if (!env.SUBOJ) return json(503, { ok: false });
  let d: any;
  try { d = await request.json(); } catch { return json(400, { ok: false }); }
  const den = String(d.den ?? ''), volba = String(d.volba ?? '');
  if (!platnyDen(den) || !MESTA.includes(volba)) return json(400, { ok: false });
  const p = await pocty(env.SUBOJ, den);
  p[volba] = (p[volba] ?? 0) + 1; // pri veľkom súčasnom prístupe sa môže pár hlasov stratiť – na orientačný súhrn stačí
  await env.SUBOJ.put(`suboj:${den}`, JSON.stringify(p), { expirationTtl: 60 * 864e2 });
  return json(200, { ok: true, pocty: p });
};
