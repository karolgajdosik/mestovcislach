// Dátové štúdio – časový rad jedného ukazovateľa pre všetky obce (poradie ako /data/studio/obce.json).
import type { APIRoute, GetStaticPaths } from 'astro';
import { casoveRady } from '../../../../lib/studio-ukazovatele';

export const getStaticPaths: GetStaticPaths = () => casoveRady().map((r) => ({ params: { rad: r.id } }));

export const GET: APIRoute = ({ params }) => {
  const r = casoveRady().find((x) => x.id === params.rad)!;
  return new Response(JSON.stringify(r), { headers: { 'Content-Type': 'application/json' } });
};
