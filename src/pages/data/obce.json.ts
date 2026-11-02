// Index obcí pre úvodný filter a vyhľadávanie: kraje, okresy a obce (názov, okres, adresa, obyvatelia) – kompaktne.
import type { APIRoute } from 'astro';
import { kraje, odkaz } from '../../lib/obce';

export const GET: APIRoute = () => {
  const k = kraje();
  const okresy: [number, string, string][] = [];
  const obce: [string, number, string, number][] = [];
  k.forEach((kr, ki) => kr.okresy.forEach((o) => {
    const oi = okresy.push([ki, o.nazov, `/${kr.slug}/${o.slug}`]) - 1;
    for (const x of o.obce) obce.push([x.nazov, oi, odkaz(x), x.obyvatelia ?? 0]);
  }));
  return new Response(JSON.stringify({ kraje: k.map((x) => [x.nazov, `/${x.slug}`]), okresy, obce }), { headers: { 'Content-Type': 'application/json' } });
};
