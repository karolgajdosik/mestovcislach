// Prihlásenie na e-mailové upozornenia: POST { email, kanal, suhlas, web (pasca na roboty) }.
// Adresa ide rovno do Brevo s dvojitým potvrdením (double opt-in) – my ju nikde neukladáme ani nelogujeme.
// Zoznamy a šablónu vytvára scripts/odber_email.py nastavenie → /data/odber-brevo.json.
const EMAIL = /^[^\s@<>()[\]\\,;:"]{1,64}@[^\s@<>()[\]\\,;:"]{1,190}\.[a-z]{2,24}$/i;
const odpoved = (stav: number, sprava: string) =>
  new Response(JSON.stringify({ ok: stav < 300, sprava }), { status: stav, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });

export const onRequestPost = async ({ request, env }: any) => {
  if (!env.BREVO_API_KEY) return odpoved(503, 'E-mailové upozornenia sa ešte pripravujú.');
  let d: any;
  try { d = await request.json(); } catch { return odpoved(400, 'Neplatná požiadavka.'); }
  if (d.web) return odpoved(200, 'Skontrolujte si e-mail.'); // vyplnené skryté pole = robot
  const email = String(d.email ?? '').trim();
  if (!EMAIL.test(email) || email.length > 254) return odpoved(400, 'Skontrolujte, prosím, e-mailovú adresu.');
  if (d.suhlas !== true) return odpoved(400, 'Bez súhlasu vám nemôžeme upozornenia posielať.');
  const mapa = await (await env.ASSETS.fetch(new URL('/data/odber-brevo.json', request.url))).json().catch(() => null);
  const kanal = String(d.kanal ?? '');
  const zoznam = mapa?.zoznamy?.[kanal];
  if (!zoznam || !mapa.sablona) return odpoved(400, 'Neznámy kanál upozornení.');
  const r = await fetch('https://api.brevo.com/v3/contacts/doubleOptinConfirmation', {
    method: 'POST',
    headers: { 'api-key': env.BREVO_API_KEY, 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({
      email, includeListIds: [zoznam], templateId: mapa.sablona,
      redirectionUrl: `https://mestovcislach.sk/odber-potvrdeny/?k=${encodeURIComponent(kanal)}`,
      attributes: { KANAL: kanal },
    }),
  });
  if (r.ok) return odpoved(200, 'Poslali sme vám e-mail – odber začne po kliknutí na „Potvrdiť odber“.');
  return odpoved(502, 'Prihlásenie sa teraz nepodarilo, skúste to, prosím, neskôr.');
};
