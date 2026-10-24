// Zoznam zastávok, liniek a kalendár služieb pre stránku Odchody MHD (odchody zo zastávky: /data/odchody/<mesto>/<id>.json).
import type { APIRoute } from 'astro';
import { MESTA } from '../../../mesta';
import { odchody } from '../../../lib/odchody';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne && odchody(m.slug)).map((m) => ({ params: { mesto: m.slug } }));
}
export const GET: APIRoute = ({ params }) => {
  const d = odchody(params.mesto!)!;
  const { odchody: _, smery: __, ...zvysok } = d;
  return new Response(JSON.stringify(zvysok), { headers: { 'Content-Type': 'application/json' } });
};
