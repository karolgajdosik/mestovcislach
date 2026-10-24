// Odchody z jednej zastávky (všetky služby; ktoré platia dnes, určí prehliadač podľa kalendára).
import type { APIRoute } from 'astro';
import { MESTA } from '../../../../mesta';
import { odchody } from '../../../../lib/odchody';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne && odchody(m.slug)).flatMap((m) => {
    const d = odchody(m.slug)!;
    return d.zastavky.map((z) => ({ params: { mesto: m.slug, id: z.id } }));
  });
}
export const GET: APIRoute = ({ params }) => {
  const d = odchody(params.mesto!)!;
  const vzory = d.odchody[params.id!] ?? [];
  // smery len použité na tejto zastávke
  const sm: string[] = [], mapa = new Map<number, number>();
  const out = vzory.map(([l, h, s, c]) => {
    if (!mapa.has(h)) { mapa.set(h, sm.length); sm.push(d.smery[h]); }
    return [l, mapa.get(h)!, s, c];
  });
  return new Response(JSON.stringify({ smery: sm, odchody: out }), { headers: { 'Content-Type': 'application/json' } });
};
