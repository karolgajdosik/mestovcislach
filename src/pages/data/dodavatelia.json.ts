// Index dodávateľov pre vyhľadávanie: [IČO, názov, počet zmlúv, suma, posledná zmluva, mestá]
import type { APIRoute } from 'astro';
import { dodavatelia } from '../../lib/dodavatelia';

export const GET: APIRoute = () => {
  const x = [...dodavatelia().values()].sort((a, b) => b.suma - a.suma)
    .map((d) => [d.ico, d.nazov, d.pocet, Math.round(d.suma), d.posledna, Object.keys(d.mesta)]);
  return new Response(JSON.stringify(x), { headers: { 'Content-Type': 'application/json' } });
};
