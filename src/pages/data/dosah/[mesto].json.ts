// Dosah MHD zo zastávok (scripts/zber_odchody.py → data/dosah/<mesto>.json); názvy a polohy zastávok sú v /data/odchody/<mesto>.json.
import type { APIRoute } from 'astro';
import fs from 'node:fs';
import path from 'node:path';
import { MESTA } from '../../../mesta';

const subor = (slug: string) => path.join(process.cwd(), 'data', 'dosah', `${slug}.json`);
export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne && fs.existsSync(subor(m.slug))).map((m) => ({ params: { mesto: m.slug } }));
}
export const GET: APIRoute = ({ params }) => new Response(fs.readFileSync(subor(params.mesto!), 'utf-8'), { headers: { 'Content-Type': 'application/json' } });
