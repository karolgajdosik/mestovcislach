// Kľúčové ukazovatele všetkých obcí pre porovnanie dvoch obcí (/porovnaj-obce/) a mapu obcí – jeden kompaktný súbor.
import type { APIRoute } from 'astro';
import { POLIA, ukazovatele, rokyUkazovatelov } from '../../lib/ukazovatele-obci';

export const GET: APIRoute = () => {
  const obce = ukazovatele().map(({ o, url, h }) => [o.kod, o.nazov, o.okres, url, ...POLIA.map(([k]) => h[k] ?? null), o.poloha ? o.poloha[0] : null, o.poloha ? o.poloha[1] : null]);
  return new Response(JSON.stringify({ polia: POLIA, roky: rokyUkazovatelov(), obce }), { headers: { 'Content-Type': 'application/json' } });
};
