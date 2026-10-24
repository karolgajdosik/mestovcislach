// Odhlásenie zo sledovania dodávateľov jedným klikom z e-mailu: /api/odhlasit?e=<adresa>&t=<podpis>.
// Podpis = HMAC-SHA256(BREVO_API_KEY, "odhlasit:" + adresa malými písmenami) – vytvára scripts/odber_email.py.
// Adresu nikam neukladáme ani nelogujeme; odstráni sa zo zoznamu „Sledovanie dodávateľov“ v Breve.
const stranka = (stav: number, nadpis: string, text: string) => new Response(`<!doctype html><html lang="sk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${nadpis} – mestovcislach.sk</title>
<style>body{margin:0;font-family:system-ui,sans-serif;background:#f7f7f5;color:#1b1d21}main{max-width:560px;margin:10vh auto;padding:24px}div{background:#fff;border:1px solid #e3e4e0;border-radius:14px;padding:24px}a{color:#c8102e;font-weight:700}</style></head>
<body><main><p style="font-weight:800;font-size:20px">mesto<span style="color:#c8102e">v</span>číslach.sk</p><div><h1 style="font-size:22px;margin-top:0">${nadpis}</h1><p>${text}</p><p><a href="/dodavatelia">Sledovanie dodávateľov</a> · <a href="/">Úvod</a></p></div></main></body></html>`,
  { status: stav, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' } });

async function podpis(kluc: string, sprava: string) {
  const k = await crypto.subtle.importKey('raw', new TextEncoder().encode(kluc), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const s = new Uint8Array(await crypto.subtle.sign('HMAC', k, new TextEncoder().encode(sprava)));
  return [...s].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export const onRequestGet = async ({ request, env }: any) => {
  const u = new URL(request.url);
  const email = (u.searchParams.get('e') ?? '').trim().toLowerCase();
  const t = u.searchParams.get('t') ?? '';
  if (!env.BREVO_API_KEY || !email || !/^[0-9a-f]{64}$/.test(t)) return stranka(400, 'Neplatný odkaz', 'Odkaz na odhlásenie nie je úplný. Skúste ho otvoriť priamo z e-mailu.');
  const ocak = await podpis(env.BREVO_API_KEY.trim(), `odhlasit:${email}`);
  // porovnanie v konštantnom čase
  let rozdiel = ocak.length ^ t.length;
  for (let i = 0; i < Math.min(ocak.length, t.length); i++) rozdiel |= ocak.charCodeAt(i) ^ t.charCodeAt(i);
  if (rozdiel) return stranka(400, 'Neplatný odkaz', 'Odkaz na odhlásenie nie je platný. Skúste ho otvoriť priamo z e-mailu.');
  const mapa = await (await env.ASSETS.fetch(new URL('/data/odber-brevo.json', request.url))).json().catch(() => null);
  const lid = mapa?.zoznamy?.dodavatel;
  if (!lid) return stranka(503, 'Skúste neskôr', 'Odhlásenie sa teraz nepodarilo.');
  const r = await fetch(`https://api.brevo.com/v3/contacts/lists/${lid}/contacts/remove`, {
    method: 'POST', headers: { 'api-key': env.BREVO_API_KEY, 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ emails: [email] }),
  });
  if (r.ok || r.status === 400) return stranka(200, 'Odhlásené', 'Zo sledovania dodávateľov sme vás odhlásili – ďalšie upozornenia na nové zmluvy vám už nepošleme.');
  return stranka(502, 'Skúste neskôr', 'Odhlásenie sa teraz nepodarilo, skúste to, prosím, o chvíľu.');
};
