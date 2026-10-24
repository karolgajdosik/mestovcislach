// Zmluvy jedného dodávateľa s mestami (posledných 50).
import type { APIRoute } from 'astro';
import { dodavatelia } from '../../../lib/dodavatelia';

export function getStaticPaths() {
  return [...dodavatelia().keys()].map((ico) => ({ params: { ico } }));
}
export const GET: APIRoute = ({ params }) => {
  const d = dodavatelia().get(params.ico!)!;
  return new Response(JSON.stringify({ ...d, suma: Math.round(d.suma), zmluvy: d.zmluvy.slice(0, 50) }), { headers: { 'Content-Type': 'application/json' } });
};
