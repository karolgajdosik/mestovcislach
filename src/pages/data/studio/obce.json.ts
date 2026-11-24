// Dátové štúdio – zoznam obcí a definícia oblastí/ukazovateľov (hodnoty sú v /data/studio/<oblast>.json, načítajú sa až keď treba).
import type { APIRoute } from 'astro';
import { OBLASTI, riadkyStudia } from '../../../lib/studio-ukazovatele';

export const GET: APIRoute = () => {
  const rr = riadkyStudia();
  const kraje = [...new Set(rr.map((x) => x.kraj))];
  const obce = rr.map((x) => [x.kod, x.n, x.okres, kraje.indexOf(x.kraj), x.url, x.h.obyv ?? null, x.lat, x.lon]);
  const oblasti = OBLASTI.map((o) => ({ ...o, polia: o.polia.map((p) => ({ ...p, pocet: rr.filter((x) => x.h[p.k] != null).length })) }));
  return new Response(JSON.stringify({ kraje, oblasti, obce }), { headers: { 'Content-Type': 'application/json' } });
};
