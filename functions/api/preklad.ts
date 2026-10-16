// Cloudflare Pages Function: strojový preklad textov webu zo slovenčiny (Workers AI, model m2m100).
// POST { jazyk: 'en'|'de'|'pl'|'hu', texty: string[] } → { preklady: string[] }
// Každý text sa ukladá do cache Cloudflare (30 dní), takže rovnaký text sa prekladá len raz.

const MODEL = '@cf/meta/m2m100-1.2b';
const JAZYKY = new Set(['en', 'de', 'pl', 'hu', 'sk']);
const MAX_TEXTOV = 60;
const MAX_DLZKA = 1200;
const LIMIT_ZA_HODINU = 4000; // nových (neuložených) prekladov na IP adresu

const json = (d: unknown, status = 200) => new Response(JSON.stringify(d), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });

async function hash(t: string) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(t));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('').slice(0, 40);
}

export async function prelozJeden(env: any, text: string, ciel: string, zdroj = 'sk'): Promise<string> {
  const cache = (caches as any).default as Cache;
  const kluc = new Request(`https://preklad.mestovcislach.sk/${zdroj}-${ciel}/${await hash(text)}`);
  const ulozene = await cache.match(kluc);
  if (ulozene) return ulozene.text();
  const r: any = await env.AI.run(MODEL, { text, source_lang: zdroj, target_lang: ciel });
  const preklad = String(r?.translated_text ?? '').trim() || text;
  await cache.put(kluc, new Response(preklad, { headers: { 'Cache-Control': 'public, max-age=2592000' } }));
  return preklad;
}

export const onRequestPost = async (ctx: any) => {
  const { request, env } = ctx;
  if (!env.AI) return json({ chyba: 'Preklad nie je dostupný.' }, 503);
  let telo: any;
  try { telo = await request.json(); } catch { return json({ chyba: 'Neplatná požiadavka.' }, 400); }
  const jazyk = String(telo.jazyk ?? '');
  if (!JAZYKY.has(jazyk) || jazyk === 'sk') return json({ chyba: 'Nepodporovaný jazyk.' }, 400);
  const texty: string[] = (Array.isArray(telo.texty) ? telo.texty : []).slice(0, MAX_TEXTOV).map((t: unknown) => String(t ?? '').slice(0, MAX_DLZKA));

  // jednoduchý limit na IP adresu (počíta sa každá požiadavka × počet textov)
  const ip = request.headers.get('CF-Connecting-IP') ?? 'x';
  const cache = (caches as any).default as Cache;
  const limitKluc = new Request(`https://limit-preklad.mestovcislach.sk/${encodeURIComponent(ip)}/${Math.floor(Date.now() / 3600e3)}`);
  const pocet = Number((await (await cache.match(limitKluc))?.text()) ?? 0);
  if (pocet > LIMIT_ZA_HODINU) return json({ chyba: 'Limit prekladov na túto hodinu.' }, 429);
  ctx.waitUntil(cache.put(limitKluc, new Response(String(pocet + texty.length), { headers: { 'Cache-Control': 'max-age=3600' } })));

  // po skupinách, aby sme nezahltili model
  const preklady: string[] = new Array(texty.length);
  for (let i = 0; i < texty.length; i += 10) {
    await Promise.all(texty.slice(i, i + 10).map(async (t, j) => {
      try { preklady[i + j] = t.trim() ? await prelozJeden(env, t, jazyk) : t; } catch { preklady[i + j] = t; }
    }));
  }
  return json({ preklady });
};
