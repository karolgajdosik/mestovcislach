// Kalendár mesta na odber (webcal) – src/lib/kalendar.ts
import type { APIRoute } from 'astro';
import { MESTA } from '../../mesta';
import { kalendar, ics } from '../../lib/kalendar';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne).map((m) => ({ params: { mesto: m.slug }, props: { nazov: m.nazov } }));
}
export const GET: APIRoute = ({ params, props }) =>
  new Response(ics(params.mesto!, (props as any).nazov, kalendar(params.mesto!)), { headers: { 'Content-Type': 'text/calendar; charset=utf-8' } });
