// Index Videozóny: všetky obce, mestá a mestské časti, ktoré majú video a prelet (stránka s PozriObec).
// [názov, typ (0 obec, 1 mesto – 141 miest so štatútom, 2 mestská časť), adresa stránky, kontext (okres / mesto), počet pamiatok v prelete]
import type { APIRoute } from 'astro';
import { kraje, odkaz, pamiatkyPreletu, kodyCasti, jeMesto } from '../../lib/obce';
import { pamiatkyMesta } from '../../lib/video-data';
import { castiMesta } from '../../lib/casti-mesta';
import { profily } from '../../lib/profil-mc';
import { MESTA } from '../../mesta';

export const GET: APIRoute = async () => {
  const out: [string, number, string, string, number][] = [];
  const videne = new Set<string>();
  const pridaj = (r: [string, number, string, string, number]) => { const k = r[2].replace(/\/$/, ''); if (!videne.has(k)) { videne.add(k); out.push(r); } };
  const mestaUrl = new Map(MESTA.filter((m) => m.aktivne).map((m) => [`/${m.slug}`, m]));
  // mestá s vlastným prehľadom (aj s mestskými časťami)
  for (const kr of kraje()) for (const ok of kr.okresy) for (const o of ok.obce) {
    const u = odkaz(o).replace(/\/$/, '');
    const m = mestaUrl.get(u);
    if (m) pridaj([m.nazov, 1, `${u}/`, m.kraj, pamiatkyMesta(o.kod, u).length]);
  }
  for (const kr of kraje()) for (const ok of kr.okresy) for (const o of ok.obce) {
    const u = odkaz(o).replace(/\/$/, '');
    if (!mestaUrl.has(u)) pridaj([o.nazov, jeMesto(o.kod) ? 1 : 0, `${u}/`, `okres ${ok.nazov}`, pamiatkyPreletu(o.kod).length]);
  }
  // mestské časti Bratislavy
  const { profily: p } = await profily();
  const kodBa = kodyCasti('bratislava');
  for (const x of p) pridaj([x.mc, 2, `/bratislava/mestske-casti/${x.slug}/`, 'Bratislava', kodBa[x.mc] ? pamiatkyPreletu(kodBa[x.mc]).length : 0]);
  // mestské časti ostatných miest
  for (const m of MESTA.filter((m) => m.aktivne && !m.plne)) {
    const c = castiMesta(m.slug);
    if (!c) continue;
    const kody = kodyCasti(m.slug);
    for (const x of c.casti) pridaj([x.n, 2, `/${m.slug}/mestske-casti/${x.slug}/`, m.nazov, kody[x.n] ? pamiatkyPreletu(kody[x.n]).length : 0]);
  }
  return new Response(JSON.stringify(out), { headers: { 'Content-Type': 'application/json' } });
};
