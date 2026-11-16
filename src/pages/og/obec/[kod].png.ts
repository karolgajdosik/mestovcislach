// Náhľadový obrázok (Open Graph 1200 × 630) pre každú obec – generuje sa pri zostavení webu (satori → SVG → resvg → PNG).
// Názov, okres a kraj, tri hlavné čísla. Bez fotiek a erbov z internetu (zostavenie nesmie závisieť od cudzích serverov).
import type { APIRoute } from 'astro';
import fs from 'node:fs';
import path from 'node:path';
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import { ukazovatele } from '../../../lib/ukazovatele-obci';

export function getStaticPaths() {
  return ukazovatele().filter((x) => x.url.split('/').filter(Boolean).length === 3).map((x) => ({ params: { kod: x.o.kod } }));
}

const PISMA = (() => {
  const d = path.join(process.cwd(), 'node_modules', '@fontsource', 'inter', 'files');
  const f = (n: string) => fs.readFileSync(path.join(d, n));
  return [
    { name: 'InterExt', data: f('inter-latin-ext-800-normal.woff'), weight: 800 as const, style: 'normal' as const },
    { name: 'Inter', data: f('inter-latin-800-normal.woff'), weight: 800 as const, style: 'normal' as const },
    { name: 'InterExt', data: f('inter-latin-ext-400-normal.woff'), weight: 400 as const, style: 'normal' as const },
    { name: 'Inter', data: f('inter-latin-400-normal.woff'), weight: 400 as const, style: 'normal' as const },
  ];
})();

const CERVENA = '#c8102e', TEXT = '#1b1d21', SIVA = '#5f636b', POZADIE = '#f7f7f5';
const fmt = (x: number) => x.toLocaleString('sk-SK', { maximumFractionDigits: 1 }).replace(/ /g, ' ');
// jednoduchý „hyperscript“ pre satori (bez JSX)
const h = (type: string, style: Record<string, unknown>, ...children: unknown[]) => ({ type, props: { style: { display: 'flex', ...style }, children: children.length === 1 ? children[0] : children } });

export const GET: APIRoute = async ({ params }) => {
  const x = ukazovatele().find((u) => u.o.kod === params.kod)!;
  const { o, kraj, h: u } = x;
  const cisla: [string, string][] = [];
  if (u.obyv != null) cisla.push([fmt(u.obyv), 'obyvateľov']);
  if (u.z10 != null) cisla.push([`${u.z10 > 0 ? '+' : u.z10 < 0 ? '−' : ''}${fmt(Math.abs(u.z10))} %`, 'obyvateľov za 10 rokov']);
  if (u.vek != null) cisla.push([`${fmt(u.vek)} r.`, 'priemerný vek']);
  else if (u.vys != null) cisla.push([`${fmt(u.vys)} m`, 'nadmorská výška']);
  const dlzka = o.nazov.length;
  const velkost = dlzka <= 12 ? 104 : dlzka <= 18 ? 88 : dlzka <= 26 ? 68 : 54;
  const strom = h('div', { width: 1200, height: 630, background: POZADIE, flexDirection: 'column', padding: '64px 72px', fontFamily: 'Inter, InterExt', color: TEXT },
    h('div', { fontSize: 30, fontWeight: 800, color: TEXT, alignItems: 'center' }, h('span', {}, 'mesto'), h('span', { color: CERVENA }, 'v'), h('span', {}, 'číslach.sk')),
    h('div', { marginTop: 54, fontSize: velkost, fontWeight: 800, letterSpacing: -2, lineHeight: 1.05 }, o.nazov),
    h('div', { marginTop: 14, fontSize: 32, color: SIVA }, `okres ${o.okres} · ${kraj}`),
    h('div', { marginTop: 'auto', gap: 22 },
      ...cisla.map(([b, s]) => h('div', { flexDirection: 'column', flex: 1, background: '#fff', border: '2px solid #e4e4e0', borderRadius: 22, padding: '22px 26px' },
        h('div', { fontSize: 50, fontWeight: 800 }, b), h('div', { fontSize: 24, color: SIVA, marginTop: 4 }, s)))),
    h('div', { position: 'absolute', left: 0, top: 0, width: 14, height: 630, background: CERVENA }, ''),
  );
  const svg = await satori(strom as any, { width: 1200, height: 630, fonts: PISMA });
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: 1200 } }).render().asPng();
  return new Response(png, { headers: { 'Content-Type': 'image/png' } });
};
