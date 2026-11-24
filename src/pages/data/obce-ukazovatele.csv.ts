// Otvorené dáta: všetky obce a všetky ukazovatele Dátového štúdia v jednom CSV (stála adresa – pre Power BI, Excel, Google Tabuľky).
// Oddeľovač bodkočiarka, desatinná čiarka, UTF-8 s BOM (Excel). Hlavička: „Oblasť: Ukazovateľ (jednotka)“.
import type { APIRoute } from 'astro';
import { OBLASTI, riadkyStudia } from '../../lib/studio-ukazovatele';

const pole = (x: string) => (/[;"\r\n]/.test(x) ? `"${x.replace(/"/g, '""')}"` : x);
const cislo = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? String(v).replace('.', ',') : '');

export const GET: APIRoute = () => {
  const polia = OBLASTI.flatMap((o) => o.polia.map((p) => ({ ...p, o: o.n })));
  const hlava = ['kod_obce', 'obec', 'okres', 'kraj', 'url', ...polia.map((p) => `${p.o}: ${p.n}${p.j ? ` (${p.j})` : ''}`), 'zemepisna_sirka', 'zemepisna_dlzka'];
  const riadky = riadkyStudia().map((x) => [
    x.kod, x.n, x.okres, x.kraj, `https://mestovcislach.sk${x.url}`, ...polia.map((p) => cislo(x.h[p.k])), cislo(x.lat), cislo(x.lon),
  ].map((v) => pole(String(v))).join(';'));
  return new Response('﻿' + [hlava.map(pole).join(';'), ...riadky].join('\r\n') + '\r\n', { headers: { 'Content-Type': 'text/csv; charset=utf-8' } });
};
