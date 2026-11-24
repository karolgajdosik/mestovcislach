// Otvorené dáta: všetky obce a ich ukazovatele v jednom CSV (stála adresa – pre Power BI, Excel, Google Tabuľky).
// Oddeľovač bodkočiarka, desatinná čiarka, UTF-8 s BOM (Excel). Rovnaké údaje ako Dátové štúdio a porovnanie obcí.
import type { APIRoute } from 'astro';
import { POLIA, ukazovatele } from '../../lib/ukazovatele-obci';

const pole = (x: string) => (/[;"\r\n]/.test(x) ? `"${x.replace(/"/g, '""')}"` : x);
const cislo = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? String(v).replace('.', ',') : '');

export const GET: APIRoute = () => {
  const hlava = ['kod_obce', 'obec', 'okres', 'kraj', 'url', ...POLIA.map(([, n, j]) => `${n}${j ? ` (${j})` : ''}`), 'zemepisna_sirka', 'zemepisna_dlzka'];
  const riadky = ukazovatele().map(({ o, url, h }) => [
    o.kod, o.nazov, o.okres, (o as any).kraj ?? '', `https://mestovcislach.sk${url}`,
    ...POLIA.map(([k]) => cislo(h[k])), cislo(o.poloha?.[0]), cislo(o.poloha?.[1]),
  ].map((x) => pole(String(x))).join(';'));
  return new Response('﻿' + [hlava.map(pole).join(';'), ...riadky].join('\r\n') + '\r\n', {
    headers: { 'Content-Type': 'text/csv; charset=utf-8' },
  });
};
