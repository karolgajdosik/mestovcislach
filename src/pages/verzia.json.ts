import type { APIRoute } from 'astro';
import { VERZIA } from '../lib/verzia';

export const GET: APIRoute = () => new Response(JSON.stringify({ v: VERZIA }), { headers: { 'Content-Type': 'application/json' } });
