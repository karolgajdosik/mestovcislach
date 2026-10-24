// Prihlásenie na e-mailové upozornenia: POST { email, kanal, suhlas, web (pasca na roboty) }; pri kanáli „dodavatel“ aj ico.
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
  // sledovanie dodávateľa: IČO musí byť medzi dodávateľmi miest; k už sledovaným IČO sa pridá (uloží sa až po potvrdení)
  const atributy: Record<string, string> = { KANAL: kanal };
  if (kanal === 'dodavatel') {
    const ico = String(d.ico ?? '');
    if (!/^\d{8}$/.test(ico)) return odpoved(400, 'Vyberte firmu zo zoznamu.');
    const znamy = await env.ASSETS.fetch(new URL(`/data/dodavatelia/${ico}.json`, request.url));
    if (!znamy.ok) return odpoved(400, 'Túto firmu nepoznáme.');
    let doteraz: string[] = [];
    const k = await fetch(`https://api.brevo.com/v3/contacts/${encodeURIComponent(email)}`, { headers: { 'api-key': env.BREVO_API_KEY, accept: 'application/json' } });
    if (k.ok) {
      const c: any = await k.json().catch(() => ({}));
      if ((c.listIds ?? []).includes(zoznam)) doteraz = String(c.attributes?.ICO ?? '').split(',').filter((x: string) => /^\d{8}$/.test(x));
    }
    // rovnaká odpoveď ako pri novom odbere – nech sa nedá zistiť, čo kto sleduje
    if (doteraz.includes(ico)) return odpoved(200, 'Poslali sme vám e-mail – odber začne po kliknutí na „Potvrdiť odber“.');
    atributy.ICO = [...doteraz, ico].slice(-25).join(',');
  }
  const r = await fetch('https://api.brevo.com/v3/contacts/doubleOptinConfirmation', {
    method: 'POST',
    headers: { 'api-key': env.BREVO_API_KEY, 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({
      email, includeListIds: [zoznam], templateId: mapa.sablona,
      redirectionUrl: `https://mestovcislach.sk/odber-potvrdeny/?k=${encodeURIComponent(kanal)}`,
      attributes: atributy,
    }),
  });
  if (r.ok) return odpoved(200, 'Poslali sme vám e-mail – odber začne po kliknutí na „Potvrdiť odber“.');
  return odpoved(502, 'Prihlásenie sa teraz nepodarilo, skúste to, prosím, neskôr.');
};
