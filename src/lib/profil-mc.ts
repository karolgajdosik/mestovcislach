// Profil mestskej časti – spája údaje zo všetkých zberov webu (počíta sa pri zostavení webu).
// Používajú ho stránky /mestske-casti, vyhľadávanie a asistent.
import fs from 'node:fs';
import path from 'node:path';

const nacitaj = (subor: string, verejne = false) => {
  const p = path.join(process.cwd(), verejne ? 'public/data' : 'data', subor);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null;
};
const tabulka = (pref: string) => {
  const dir = path.join(process.cwd(), 'public', 'data', 'tabulky');
  const f = fs.existsSync(dir) ? fs.readdirSync(dir).find((x) => x.startsWith(pref)) : null;
  return f ? { ...JSON.parse(fs.readFileSync(path.join(dir, f), 'utf-8')), id: f.replace('.json', '') } : null;
};

export const slug = (mc: string) => mc.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, '-');

// bod v polygóne (GeoJSON Polygon/MultiPolygon, [lon, lat])
function vPolygone(lon: number, lat: number, geo: any): boolean {
  const polygony = geo.type === 'Polygon' ? [geo.coordinates] : geo.coordinates;
  return polygony.some((poly: number[][][]) => {
    let dnu = false;
    const r = poly[0];
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [xi, yi] = r[i], [xj, yj] = r[j];
      if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) dnu = !dnu;
    }
    return dnu;
  });
}

export type Porovnanie = { hodnota: number | null; mesto: number | null; poradie?: number | null };
export type Profil = {
  mc: string; slug: string; kod: string; okres: string;
  obyvatelia: { pocet: number | null; rok: string; roky: [string, number][]; zmena10: number | null; rozloha: number | null; hustota: number | null };
  sklad: Record<'seniori' | 'deti' | 'vs' | 'pracujuci' | 'vlastne_byty', Porovnanie>;
  prognoza: { r2022: number | null; r2035: number | null; zmena: number | null; vek2035: number | null; starnutie2035: number | null; poradie: number | null };
  rozvoj: Porovnanie & { kraj: number | null };
  nezamestnanost: { okres: string; mesiac: string | null; pdu: number | null; uchadzaci: number | null; slovensko: number | null } | null;
  volby: {
    starosta: { meno: string; strany: string; podiel: number; ucast: number } | null;
    starosta_kandidati: { meno: string; strany: string; podiel: number }[];
    primator: { ucast: number | null; poradie: { meno: string; podiel: number }[] } | null;
    nrsr: { ucast: number; strany: { nazov: string; podiel: number }[] } | null;
    ep: { ucast: number; strany: { nazov: string; podiel: number }[] } | null;
  };
  financie: { dlh: number | null; pomer: number | null; prijmy: number | null; rok: string | null; zmluv: number | null; suma_zmluv: number | null; partneri: { nazov: string; suma: number; zmluv: number }[]; dotacie: { nazov: string; suma: number }[]; dotacie_suma: number | null };
  skoly: Record<string, { skol: number; ziakov: number }> | null;
  socialne: Record<string, number> | null;
  bezpecnost: { priestupky: number | null; trestne: number | null; na1000: Porovnanie; najcastejsie: string[]; podnety: number | null; obdobie: string };
  klima: { horucavy: Porovnanie; zrazky: Porovnanie };
  miesta: Record<string, number>;
};

let cache: { profily: Profil[]; mesto: any } | null = null;

export async function profily(): Promise<{ profily: Profil[]; mesto: any }> {
  if (cache) return cache;
  const obyv = nacitaj('obyvatelstvo-bratislava.json');
  const hranice = nacitaj('hranice-bratislava.geojson');
  const scit = nacitaj('scitanie-bratislava.json');
  const ukaz = nacitaj('mc-ukazovatele.json');
  const nez = nacitaj('nezamestnanost-bratislava.json');
  const kom = nacitaj('komunalne-bratislava.json');
  const volby = nacitaj('volby-bratislava.json');
  const zmc = nacitaj('zmluvy-mc.json');
  const skoly = nacitaj('skoly-iedu.json');
  const soc = nacitaj('socialne-bratislava.json');
  const bez = nacitaj('bezpecnost-bratislava.json');
  const progPocet = tabulka('35e2060c'), progVek = tabulka('d97203f6'), progStarnutie = tabulka('a2042a88');
  const hodnota = (t: any, mc: string, rok: number) => t?.riadky.find((r: any[]) => r[0] === mc && Number(r[1]) === rok)?.[2] ?? null;

  const rok = obyv ? Object.keys(obyv.mesto.roky).sort().pop()! : '';
  const rok10 = String(Number(rok) - 10);
  const casti: any[] = obyv?.mestske_casti ?? [];
  const geo = new Map<string, any>((hranice?.features ?? []).map((f: any) => [f.properties.kod_obce, f]));

  // podiely zo sčítania (mesto aj mestské časti)
  const podiel = (tema: string, kat: RegExp, mc: string | null, menovatel?: (d: any) => number) => {
    const t = scit?.temy?.[tema];
    if (!t) return null;
    const d = mc ? t.mestske_casti[mc] : t.mesto;
    if (!d) return null;
    const cit = Object.entries<number>(d).filter(([k]) => k !== 'Spolu' && kat.test(k)).reduce((a, [, v]) => a + v, 0);
    const men = menovatel ? menovatel(d) : d.Spolu;
    return men ? (100 * cit) / men : null;
  };
  const bezDeti = (d: any) => d.Spolu - (Object.entries<number>(d).find(([k]) => /0-14 rokov/.test(k))?.[1] ?? 0);
  const SKLAD: Record<string, (mc: string | null) => number | null> = {
    seniori: (mc) => podiel('vek', /^65/, mc),
    deti: (mc) => podiel('vek', /^14 rokov/, mc),
    vs: (mc) => podiel('vzdelanie', /^Vysokoškolské/, mc, bezDeti),
    pracujuci: (mc) => podiel('ekonomicka_aktivita', /^Ekonomicky aktívny/, mc),
    vlastne_byty: (mc) => podiel('byty_vlastnictvo', /^vlastný byt|^byt vo vlastnom/, mc),
  };

  // klimatický atlas: priemer buniek v polygóne mestskej časti
  const klimaPriemer = (vrstva: string) => {
    const d = nacitaj(`klima/${vrstva}.json`, true);
    const vysl = new Map<string, number>();
    if (!d) return { vysl, mesto: null as number | null };
    const sumy = new Map<string, [number, number]>();
    let s = 0, n = 0;
    for (const [s1, w, n1, e, v] of d.bunky as number[][]) {
      const lat = (s1 + n1) / 2, lon = (w + e) / 2;
      s += v; n++;
      for (const [kod, f] of geo) if (vPolygone(lon, lat, f.geometry)) { const x = sumy.get(kod) ?? [0, 0]; sumy.set(kod, [x[0] + v, x[1] + 1]); break; }
    }
    for (const [kod, [a, b]] of sumy) vysl.set(kod, a / b);
    return { vysl, mesto: n ? s / n : null };
  };
  const horucavy = klimaPriemer('riziko_horucavy');
  const zrazky = klimaPriemer('riziko_zrazky_budovy');

  // miesta (rovnaký zoznam ako pre asistenta a vyhľadávanie)
  let miesta: any[] = [];
  try {
    const asistent = await import('../pages/data/asistent.json.ts');
    miesta = (await (await asistent.GET()).json()).miesta ?? [];
  } catch { /* bez miest */ }

  const k22 = kom?.volby?.find((v: any) => v.id === '2022');
  const nrsr = volby?.volby?.find((v: any) => v.id.startsWith('nrsr'));
  const ep = volby?.volby?.find((v: any) => v.id.startsWith('ep'));
  const mesiace = Object.keys(nez?.mesacne ?? {}).sort();
  const mesiac = mesiace[mesiace.length - 1] ?? null;
  const okresMc = (mc: string) => Object.entries<string>(nez?.okresy_mc ?? {}).find(([, v]) => v.split(', ').includes(mc))?.[0]?.replace('Okres ', '') ?? '';
  const dlhRok = ukaz?.dlh ? Object.keys(ukaz.dlh.roky).sort().pop()! : null;
  const obdobieBez = bez?.priestupky?.roky ? `${Object.keys(bez.priestupky.roky)[0]}–${Object.keys(bez.priestupky.roky).pop()}` : '';
  const pocetMesto = obyv ? obyv.mesto.roky[rok] : null;

  const profily: Profil[] = casti.map((c) => {
    const mc: string = c.nazov_kratky;
    const kod = String(c.kod).slice(-6);
    const f = geo.get(kod);
    const pocet = c.roky[rok] ?? null;
    const rozloha = f?.properties.rozloha_km2 ?? null;
    const p22 = hodnota(progPocet, mc, 2022), p35 = hodnota(progPocet, mc, 2035);
    const st = k22?.oso?.starostovia?.find((s: any) => s.nazov === mc || s.kod === kod);
    const vit = st?.kandidati?.find((k: any) => k.zvoleny);
    const pr = k22?.oso?.primator?.mestske_casti?.find((s: any) => s.nazov === mc || s.kod === kod);
    const vNrsr = nrsr?.mestske_casti?.find((s: any) => s.kod_obce === kod);
    const vEp = ep?.mestske_casti?.find((s: any) => s.kod_obce === kod);
    const z = zmc?.mestske_casti?.[mc];
    const dot = zmc?.dotacie?.[mc]?.poskytnute ?? zmc?.dotacie?.[mc];
    const dl = dlhRok ? ukaz.dlh.roky[dlhRok][mc] : null;
    const pri = bez?.priestupky?.mestske_casti?.[mc];
    const tc = bez?.trestne_ciny?.mestske_casti?.[mc];
    const okres = okresMc(mc);
    const nm = mesiac ? nez.mesacne[mesiac] : null;
    const pocty: Record<string, number> = {};
    for (const m of miesta) if (m.c === mc) pocty[m.k] = (pocty[m.k] ?? 0) + 1;
    return {
      mc, slug: slug(mc), kod, okres,
      obyvatelia: { pocet, rok, roky: Object.entries<number>(c.roky).sort(), zmena10: pocet && c.roky[rok10] ? (100 * (pocet - c.roky[rok10])) / c.roky[rok10] : null, rozloha, hustota: pocet && rozloha ? pocet / rozloha : null },
      sklad: Object.fromEntries(Object.entries(SKLAD).map(([k, fn]) => [k, { hodnota: fn(mc), mesto: fn(null) }])) as Profil['sklad'],
      prognoza: { r2022: p22, r2035: p35, zmena: p22 && p35 ? (100 * (p35 - p22)) / p22 : null, vek2035: hodnota(progVek, mc, 2035), starnutie2035: hodnota(progStarnutie, mc, 2035), poradie: null },
      rozvoj: { hodnota: ukaz?.index_rozvoja?.mestske_casti?.[mc] ?? null, mesto: null, kraj: ukaz?.index_rozvoja?.priemer_kraja ?? null, poradie: null },
      nezamestnanost: okres && nm ? { okres, mesiac, pdu: nm[okres]?.pdu ?? null, uchadzaci: nm[okres]?.uoz ?? null, slovensko: nm['Slovenská republika']?.pdu ?? null } : null,
      volby: {
        starosta: vit ? { meno: vit.meno, strany: vit.strany, podiel: vit.podiel, ucast: st.ucast?.ucast_pct } : null,
        starosta_kandidati: (st?.kandidati ?? []).slice(0, 5).map((k: any) => ({ meno: k.meno, strany: k.strany, podiel: k.podiel })),
        primator: pr ? { ucast: pr.ucast ?? null, poradie: pr.poradie ?? [] } : null,
        nrsr: vNrsr ? { ucast: vNrsr.ucast, strany: vNrsr.strany.slice(0, 6).map((s: any) => ({ nazov: s.nazov, podiel: s.podiel })) } : null,
        ep: vEp ? { ucast: vEp.ucast, strany: vEp.strany.slice(0, 6).map((s: any) => ({ nazov: s.nazov, podiel: s.podiel })) } : null,
      },
      financie: {
        dlh: dl?.dlh ?? null, pomer: dl?.pomer ?? null, prijmy: dl?.prijmy ?? null, rok: dlhRok,
        zmluv: z?.zmluv ?? null, suma_zmluv: z?.suma ?? null,
        partneri: (z?.najvacsi_partneri ?? []).slice(0, 5).map((p: any) => ({ nazov: p.nazov, suma: p.suma, zmluv: p.zmluv })),
        dotacie: (dot?.prijimatelia ?? []).slice(0, 5), dotacie_suma: dot?.suma ?? null,
      },
      skoly: skoly?.mestske_casti?.[mc] ?? null,
      socialne: soc?.mestske_casti?.[mc] ?? null,
      bezpecnost: {
        priestupky: pri?.spolu ?? null, trestne: tc?.spolu ?? null,
        na1000: { hodnota: pri && pocet ? (1000 * pri.spolu) / pocet / Object.keys(pri.roky).length : null, mesto: bez && pocetMesto ? (1000 * bez.priestupky.spolu) / pocetMesto / Object.keys(bez.priestupky.roky).length : null },
        najcastejsie: pri?.najcastejsie ?? [], podnety: bez?.podnety?.mestske_casti?.[mc] ?? null, obdobie: obdobieBez,
      },
      klima: { horucavy: { hodnota: horucavy.vysl.get(kod) ?? null, mesto: horucavy.mesto }, zrazky: { hodnota: zrazky.vysl.get(kod) ?? null, mesto: zrazky.mesto } },
      miesta: pocty,
    };
  });

  // poradia medzi 17 časťami (1 = najvyššie)
  const poradie = (hodnoty: (number | null)[]) => { const s = hodnoty.filter((x): x is number => x != null).sort((a, b) => b - a); return (x: number | null) => (x == null ? null : s.indexOf(x) + 1); };
  const pRozvoj = poradie(profily.map((p) => p.rozvoj.hodnota));
  const pProg = poradie(profily.map((p) => p.prognoza.zmena));
  const pHor = poradie(profily.map((p) => p.klima.horucavy.hodnota));
  const pZr = poradie(profily.map((p) => p.klima.zrazky.hodnota));
  const pBez = poradie(profily.map((p) => p.bezpecnost.na1000.hodnota));
  const pSkl: Record<string, (x: number | null) => number | null> = Object.fromEntries(Object.keys(SKLAD).map((k) => [k, poradie(profily.map((p) => (p.sklad as any)[k].hodnota))]));
  for (const p of profily) {
    p.rozvoj.poradie = pRozvoj(p.rozvoj.hodnota);
    p.prognoza.poradie = pProg(p.prognoza.zmena);
    p.klima.horucavy.poradie = pHor(p.klima.horucavy.hodnota);
    p.klima.zrazky.poradie = pZr(p.klima.zrazky.hodnota);
    p.bezpecnost.na1000.poradie = pBez(p.bezpecnost.na1000.hodnota);
    for (const k of Object.keys(SKLAD)) (p.sklad as any)[k].poradie = pSkl[k]((p.sklad as any)[k].hodnota);
  }
  profily.sort((a, b) => a.mc.localeCompare(b.mc, 'sk'));
  cache = { profily, mesto: { pocet: pocetMesto, rok, k22: k22 ?? null } };
  return cache;
}
