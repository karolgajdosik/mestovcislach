// Najnovšie novinky mesta a najbližší termín z kalendára – pre „Môj prehľad“ na úvodnej stránke.
import type { APIRoute } from 'astro';
import { MESTA } from '../../../mesta';
import { novinky, TYPY_NOVINIEK } from '../../../lib/novinky';
import { kalendar } from '../../../lib/kalendar';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne).map((m) => ({ params: { mesto: m.slug } }));
}
export const GET: APIRoute = ({ params }) => {
  const s = params.mesto!;
  const videne = new Set<string>();
  const n = novinky(s, 60).filter((x) => !videne.has(x.nazov) && !!videne.add(x.nazov)).slice(0, 4).map((x) => ({ datum: x.datum, typ: TYPY_NOVINIEK[x.typ], nazov: x.nazov, odkaz: x.odkaz }));
  const dnes = new Date().toISOString().slice(0, 10);
  const terminy = kalendar(s).filter((u) => (u.do ?? u.od) >= dnes).slice(0, 2).map((u) => ({ od: u.od, do: u.do, nazov: u.nazov, odkaz: u.odkaz }));
  return new Response(JSON.stringify({ novinky: n, terminy }), { headers: { 'Content-Type': 'application/json' } });
};
