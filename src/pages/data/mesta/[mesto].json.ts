// Podklady AI asistenta pre krajské mestá okrem Bratislavy (/data/mesta/<slug>.json).
// Zdroj: data/mesta/<slug>.json (scripts/zber_mesta.py), stavebné zámery a katalóg mesta.
import fs from 'node:fs';
import path from 'node:path';
import { MESTA } from '../../../mesta';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne && !m.plne).map((m) => ({ params: { mesto: m.slug } }));
}

const citaj = (...c: string[]) => {
  const p = path.join(process.cwd(), ...c);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null;
};
const podiel = (t: Record<string, number> | undefined, n = 6) => {
  if (!t) return undefined;
  const spolu = t.Spolu ?? Object.values(t).reduce((a, b) => a + b, 0);
  return Object.fromEntries(Object.entries(t).filter(([k]) => k !== 'Spolu').sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => [k, `${((100 * v) / spolu).toFixed(1)} %`]));
};

export async function GET({ params }: { params: { mesto: string } }) {
  const m = MESTA.find((x) => x.slug === params.mesto)!;
  const d = citaj('data', 'mesta', `${m.slug}.json`) ?? {};
  const por = citaj('data', 'mesta', 'porovnanie.json')?.mesta ?? [];
  const eia = citaj('public', 'data', 'mesta', `eia-${m.slug}.json`);
  const kat = citaj('data', `katalog-stav-${m.slug}.json`);
  const roky = d.obyvatelia?.roky ?? {};
  const kom = d.komunalne ?? {};
  const pr = d.praca?.mesacne ?? {};
  const prPosl = Object.keys(pr).sort().pop();
  const hranica = new Date(Date.now() - 2 * 365 * 864e5).toISOString().slice(0, 10);
  const fakty = {
    mesto: { nazov: m.nazov, kraj: m.kraj, okresy: m.okresy },
    obyvatelia_k_31_12: Object.fromEntries(Object.entries(roky).filter(([r]) => Number(r) >= 2005)),
    obyvatelia_mestskych_casti_posledny_rok: Object.fromEntries(Object.entries<any>(d.obyvatelia?.casti ?? {}).map(([c, r]) => [c, r[Object.keys(r).sort().pop()!]])),
    scitanie_2021: d.scitanie ? { vek: podiel(d.scitanie.vek, 4), vzdelanie: podiel(d.scitanie.vzdelanie, 7), narodnost: podiel(d.scitanie.narodnost, 6), nabozenstvo: podiel(d.scitanie.nabozenstvo, 6), byty_vlastnictvo: podiel(d.scitanie.byty_vlastnictvo, 5) } : undefined,
    volby: d.volby ? Object.fromEntries(Object.entries<any>(d.volby).map(([k, v]) => [v.nazov, { ucast: `${v.ucast} % (Slovensko ${v.ucast_sr} %)`, strany: v.strany.slice(0, 8).map((s: any) => `${s.nazov} ${s.podiel} %`) }])) : undefined,
    komunalne_volby: Object.fromEntries(Object.entries<any>(kom).map(([rok, v]) => [rok, {
      ucast: v.ucast ? `${v.ucast.ucast_pct} %` : undefined,
      primator: v.primator.slice(0, 6).map((k: any) => `${k.meno} (${k.strany.slice(0, 120)}) ${k.podiel} %${k.zvoleny ? ' – zvolený' : ''}`),
      zastupitelstvo_mandaty: v.zastupitelstvo.mandaty.map((x: any) => `${x.strany.slice(0, 120)}: ${x.mandaty}`),
    }])),
    nezamestnanost_pdu: prPosl ? { obdobie: prPosl, ...Object.fromEntries(Object.entries<any>(pr[prPosl]).map(([o, v]) => [o, `PDU ${v.pdu} %, uchádzačov ${v.uoz}`])) } : undefined,
    byty_v_okresoch: d.byty ? Object.fromEntries(Object.entries<any>(d.byty).slice(-10).map(([r, v]) => [r, `dokončené ${v.DOKONC_BYT}, začaté ${v.ZAC_BYT}`])) : undefined,
    ceny_byvania_kraj_medzirocne: d.ceny?.kraj ? Object.fromEntries(Object.entries(d.ceny.kraj).slice(-6).map(([q, v]) => [q, `${v} % (SR ${d.ceny.sr?.[q]} %)`])) : undefined,
    stavebne_zamery_eia: eia ? {
      poznamka: 'Zámery v posudzovaní vplyvov na životné prostredie (Enviroportál).',
      prave_sa_posudzuje: eia.zamery.filter((z: any) => !z.ukoncene).length,
      zamery: eia.zamery.filter((z: any) => !z.ukoncene || z.zmena >= hranica).slice(0, 40).map((z: any) => `${z.nazov} (${z.stav}${z.ukoncene ? ', posudzovanie skončené' : ', práve sa posudzuje'}; zmena ${z.zmena}${z.navrhovatel ? `; ${z.navrhovatel}` : ''}) – ${(z.ucel ?? '').slice(0, 160)}`),
    } : undefined,
    porovnanie_krajskych_miest: por.map((p: any) => `${p.nazov}: ${p.obyvatelia} obyv. (${p.zmena10} % za 10 r.), seniori ${p.seniori} %, VŠ ${p.vs} %, PDU ${p.pdu} %, účasť komunálne ${p.ucast_komunalne} %`),
    katalog_dat_mesta: kat ? kat.datasety.filter((x: any) => x.stav === 'katalog').map((x: any) => `${x.nazov} – /${m.slug}/katalog/${x.id}`) : undefined,
  };
  return new Response(JSON.stringify(fakty), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
