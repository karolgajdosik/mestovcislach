// Dátové štúdio – hodnoty ukazovateľov jednej oblasti pre všetky obce (v poradí ako /data/studio/obce.json).
import type { APIRoute, GetStaticPaths } from 'astro';
import { OBLASTI, riadkyStudia } from '../../../lib/studio-ukazovatele';

export const getStaticPaths: GetStaticPaths = () => OBLASTI.map((o) => ({ params: { oblast: o.id } }));

export const GET: APIRoute = ({ params }) => {
  const ob = OBLASTI.find((o) => o.id === params.oblast)!;
  const rr = riadkyStudia();
  const h: Record<string, (number | null)[]> = {};
  for (const p of ob.polia) h[p.k] = rr.map((x) => x.h[p.k] ?? null);
  return new Response(JSON.stringify({ id: ob.id, h }), { headers: { 'Content-Type': 'application/json' } });
};
