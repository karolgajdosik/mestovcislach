// Podklady pre stránku „Moja adresa“: miesta s polohou podľa kategórií, hranice mestských častí,
// pri Bratislave aj spádové obvody ZŠ, zvolení zástupcovia podľa MČ a stavebné zámery (EIA) podľa MČ.
// Všetko sa počíta až v prehliadači – na server sa poloha neposiela.
import type { APIRoute } from 'astro';
import { MESTA } from '../../../../mesta';
import { mapaMesta } from '../../../../lib/mapa';
import { citaj, r5, zjednodus, kategorieBA, kategorieMesta } from '../../../../lib/adresa';
import { obdobia } from '../../../../lib/zastupitelstvo';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne).map((m) => ({ params: { mesto: m.slug } }));
}

// zvolení zástupcovia podľa MČ (Bratislava: starosta MČ a mestskí poslanci z obvodu, len meno a strana)
function zastupcoviaBA() {
  const d = citaj('data', 'komunalne-bratislava.json');
  const v = (d?.volby ?? []).filter((x: any) => x.oso).sort((a: any, b: any) => b.id.localeCompare(a.id))[0];
  if (!v) return null;
  const mc: Record<string, any> = {};
  for (const s of v.oso.starostovia ?? []) {
    const z = s.kandidati?.find((k: any) => k.zvoleny);
    mc[s.nazov] = { starosta: z ? { meno: z.meno, strany: z.strany } : null, poslanci: [] };
  }
  for (const p of v.oso.mestske_zastupitelstvo?.zvoleni ?? []) {
    for (const n of String(p.obvod).split(', ')) (mc[n] ??= { starosta: null, poslanci: [] }).poslanci.push({ meno: p.meno, strany: p.strany });
  }
  return { rok: v.id, priebezne: !!v.spracovanie?.priebezne, mc };
}

// Košice: mestskí poslanci podľa obvodu (obvod = skupina mestských častí), len meno a strana
function zastupcoviaObvody(slug: string) {
  const o = obdobia(slug).find((x) => !x.priebezne && x.poslancov > 0);
  if (!o || !o.poslanci.some((p) => p.obvod && !/^obvod č\./.test(p.obvod))) return null;
  const mc: Record<string, any> = {};
  for (const p of o.poslanci) for (const n of String(p.obvod).split(', ')) (mc[n] ??= { starosta: null, poslanci: [] }).poslanci.push({ meno: p.meno, strany: p.strany });
  return { rok: o.rok, priebezne: false, mc };
}

function eiaBA() {
  const d = citaj('public', 'data', 'eia.json');
  if (!d) return null;
  const mc: Record<string, any[]> = {};
  for (const z of d.zamery) {
    if (String(z.ukoncene) === 'True' || z.ukoncene === true) continue;
    const casti: string[] = Array.isArray(z.mc) ? z.mc : String(z.mc ?? '').replace(/[[\]']/g, '').split(',').map((s) => s.trim()).filter(Boolean);
    for (const c of casti) (mc[c] ??= []).push({ nazov: String(z.nazov).replace(/^"|"$/g, ''), stav: z.stav, od: z.od, id: z.id });
  }
  for (const k of Object.keys(mc)) mc[k].sort((a, b) => String(b.od).localeCompare(String(a.od)));
  return mc;
}

export const GET: APIRoute = ({ params }) => {
  const m = MESTA.find((x) => x.slug === params.mesto)!;
  const ba = m.slug === 'bratislava';
  const hranice = ba ? citaj('data', 'hranice-bratislava.geojson') : mapaMesta(m.slug)?.hranice;
  const mc = hranice?.features
    ?.filter((f: any) => ['Polygon', 'MultiPolygon'].includes(f.geometry?.type))
    .map((f: any) => ({ n: f.properties?.nazov ?? f.properties?.n, g: zjednodus(f.geometry) }))
    .filter((x: any) => x.n && x.g) ?? [];
  const telo = {
    mesto: m.nazov, slug: m.slug, stred: (m as any).stred,
    kategorie: ba ? kategorieBA() : kategorieMesta(m.slug),
    mestske_casti: mc.length > 1 ? mc : [],
    ...(ba ? { obvody_zs: '/data/obvody-zs-bratislava.geojson', zastupcovia: zastupcoviaBA(), eia_mc: eiaBA() } : {}),
    ...(!ba && zastupcoviaObvody(m.slug) ? { zastupcovia: zastupcoviaObvody(m.slug) } : {}),
  };
  return new Response(JSON.stringify(telo), { headers: { 'Content-Type': 'application/json' } });
};
