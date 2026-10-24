// RSS 2.0 kanál noviniek mesta (rovnaký obsah ako /<mesto>/novinky).
import type { APIRoute } from 'astro';
import { MESTA } from '../../mesta';
import { novinky, TYPY_NOVINIEK } from '../../lib/novinky';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne).map((m) => ({ params: { mesto: m.slug } }));
}
const WEB = 'https://mestovcislach.sk';
const x = (s: unknown) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[c]!).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '');

export const GET: APIRoute = ({ params }) => {
  const m = MESTA.find((y) => y.slug === params.mesto)!;
  const pol = novinky(m.slug).slice(0, 50);
  const abs = (u: string) => (/^https?:/.test(u) ? u : WEB + u);
  const items = pol.map((p) => `<item><title>${x(p.nazov)}</title><link>${x(abs(p.odkaz))}</link><guid isPermaLink="false">${x(`${m.slug}-${p.typ}-${p.datum}-${p.nazov}`)}</guid><pubDate>${new Date(p.datum + 'T08:00:00Z').toUTCString()}</pubDate><category>${x(TYPY_NOVINIEK[p.typ])}</category><description>${x(p.text)}</description></item>`).join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>${x(`Čo je nové ${m.v} – mestovcislach.sk`)}</title><link>${WEB}/${m.slug}/novinky</link><atom:link href="${WEB}/${m.slug}/novinky.xml" rel="self" type="application/rss+xml"/><description>${x(`Stavebné zámery, väčšie zmluvy a zasadnutia zastupiteľstva – ${m.nazov}`)}</description><language>sk</language>${items}</channel></rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
};
