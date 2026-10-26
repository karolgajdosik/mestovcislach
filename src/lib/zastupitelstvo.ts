// Mestské zastupiteľstvo podľa komunálnych volieb: primátor, zvolení poslanci (len meno, strana, hlasy, obvod),
// zloženie podľa strán a porovnanie s predchádzajúcim obdobím (kto mandát obhájil, kto je nový).
// Zdroje: data/komunalne-bratislava.json (Bratislava) a data/mesta/<slug>.json → komunalne (ostatné mestá).
import fs from 'node:fs';
import path from 'node:path';

export type Poslanec = { meno: string; strany: string; hlasy?: number; obvod?: string };
export type Obdobie = {
  rok: string; priebezne: boolean; ucast?: number | null;
  primator: { meno: string; strany: string; podiel?: number; hlasy?: number } | null;
  poslancov: number; mandaty: { strany: string; mandaty: number }[]; poslanci: Poslanec[];
  /** súhrn za zvolených (len počty – vek z kandidátnych listín ŠÚ SR, ženy odhadom podľa priezviska) */
  statistiky?: { zeny?: number; vek_priemer?: number; vek_min?: number; vek_max?: number; do_35?: number };
};

const citaj = (...p: string[]) => {
  const f = path.join(process.cwd(), ...p);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf-8')) : null;
};

/** Volebné obdobia od najnovšieho. */
export function obdobia(slug: string): Obdobie[] {
  const out: Obdobie[] = [];
  if (slug === 'bratislava') {
    for (const v of citaj('data', 'komunalne-bratislava.json')?.volby ?? []) {
      const o = v.oso;
      if (!o?.mestske_zastupitelstvo) continue;
      const z = o.mestske_zastupitelstvo;
      const kand = o.primator?.kandidati ?? [];
      const p = kand.find((k: any) => k.zvoleny) ?? (v.spracovanie?.priebezne ? kand[0] : null);
      out.push({
        rok: v.id, priebezne: !!v.spracovanie?.priebezne, ucast: o.primator?.ucast?.ucast_pct ?? null,
        primator: p ? { meno: p.meno, strany: p.strany, podiel: p.podiel, hlasy: p.hlasy } : null,
        poslancov: z.poslancov ?? z.zvoleni?.length ?? 0, mandaty: z.mandaty ?? [],
        poslanci: (z.zvoleni ?? []).map((x: any) => ({ meno: x.meno, strany: x.strany, hlasy: x.hlasy, obvod: x.obvod })),
        statistiky: z.statistiky,
      });
    }
  } else {
    const k = citaj('data', 'mesta', `${slug}.json`)?.komunalne ?? {};
    for (const [rok, v] of Object.entries<any>(k)) {
      if (!v?.zastupitelstvo) continue;
      const kand = v.primator ?? [];
      const p = kand.find((x: any) => x.zvoleny) ?? (v.spracovanie?.priebezne ? kand[0] : null);
      out.push({
        rok, priebezne: !!v.spracovanie?.priebezne, ucast: v.ucast?.ucast_pct ?? null,
        primator: p ? { meno: p.meno, strany: p.strany, podiel: p.podiel, hlasy: p.hlasy } : null,
        poslancov: v.zastupitelstvo.poslancov ?? 0, mandaty: v.zastupitelstvo.mandaty ?? [],
        poslanci: (v.zastupitelstvo.poslanci ?? []).map((x: any) => ({ meno: x.meno, strany: x.strany, hlasy: x.hlasy, obvod: x.obvod })),
        statistiky: v.zastupitelstvo.statistiky,
      });
    }
  }
  return out.sort((a, b) => b.rok.localeCompare(a.rok));
}

/** Meno bez titulov a s malými písmenami – ten istý človek aj pri inom zápise titulu. */
export const bezTitulov = (m: string) =>
  m.split(/[\s,]+/).filter((s) => s && !s.includes('.') && !/^(PhD|MBA|LL|MPH|DiS|CSc|DrSc|ArtD|PhDr|JUDr|MUDr|RNDr|Ing|Mgr|Bc)$/i.test(s)).join(' ').toLowerCase();

// Skratky častých strán (dlhé koaličné názvy sú inak nečitateľné)
const SKR: [RegExp, string][] = [
  [/^Progresívne Slovensko$/, 'PS'], [/^Sloboda a Solidarita$|^SaS$/, 'SaS'], [/^Kresťanskodemokratické hnutie$|^KDH$/, 'KDH'],
  [/^SMER - (sociálna demokracia|slovenská sociálna demokracia)$|^SMER-SD$/, 'Smer'], [/^HLAS - sociálna demokracia$/, 'Hlas'], [/^Slovenská národná strana$/, 'SNS'],
  [/^Strana obcí a miest - SOM SLOVENSKO$/, 'SOM Slovensko'], [/^Kotlebovci - Ľudová strana Naše Slovensko$|^ĽS Naše Slovensko$/, 'ĽSNS'],
  [/^OBYČAJNÍ ĽUDIA/, 'OĽaNO'], [/^Občianska konzervatívna strana$/, 'OKS'], [/^Demokratická únia Slovenska$/, 'DÚ'],
  [/^SME RODINA$/, 'Sme rodina'], [/^ZA ĽUDÍ$/, 'Za ľudí'], [/^DOBRÁ VOĽBA a Umiernení$/, 'Dobrá voľba'],
  [/^SZÖVETSÉG/, 'Aliancia'], [/^Hnutie Slovensko$/, 'Hnutie Slovensko'], [/^Demokrati$/, 'Demokrati'], [/^REPUBLIKA$/, 'Republika'],
  [/^Slovensko$/, 'Slovensko'], [/^nezávislý kandidát$/, 'nezávislí'],
  [/^KDH - Kresťanskodemokratické hnutie$/, 'KDH'], [/^Hnutie SLOVENSKO$/i, 'Hnutie Slovensko'], [/^SOM SLOVENSKO - Strana obcí a miest$/, 'SOM Slovensko'],
  [/^Demokratická strana - Občianski demokrati Slovenska$|^Demokratická strana$/, 'Demokratická strana'], [/^Magyar Szövetség/, 'Aliancia'],
  [/^Tím Kraj Nitra/, 'Tím Kraj Nitra'], [/^Konzervatívci - Kresťanská únia$/, 'Konzervatívci'], [/^Kresťanská únia \(KÚ\)$/, 'Kresťanská únia'],
  [/^SPOLU - občianska demokracia$/, 'Spolu'], [/^ODS - Občianski demokrati Slovenska$/, 'ODS'], [/^STAROSTOVIA A NEZÁVISLÍ KANDIDÁTI$/, 'Starostovia a nezávislí'],
];
export const skrat = (strany: string) => strany.split(', ').map((s) => SKR.find(([r]) => r.test(s.trim()))?.[1] ?? s.trim()).join(' + ');
