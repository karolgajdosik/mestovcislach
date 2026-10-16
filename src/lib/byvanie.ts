// Údaje o bývaní pre stránku /vystavba: ceny (ŠÚ SR HPI), výstavba bytov (ŠÚ SR),
// byty hlavného mesta, komunitné bývanie a príspevok na bývanie (data.bratislava.sk), sčítanie 2021.
import fs from 'node:fs';
import path from 'node:path';

const citaj = (...c: string[]) => {
  const p = path.join(process.cwd(), ...c);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf-8')) : null;
};
const tabulka = (id: string) => citaj('public', 'data', 'tabulky', `${id}.json`);
const cislo = (x: unknown) => {
  const n = typeof x === 'number' ? x : Number(String(x ?? '').replace(/\s/g, '').replace(',', '.'));
  return Number.isFinite(n) ? n : null;
};
const obdobie = (o: string) => o.replace(/^(\d{4})-Q(\d)$/, '$2. Q $1');

let cache: any = null;
export async function byvanie() {
  if (cache) return cache;
  const d = citaj('data', 'byvanie-bratislava.json');

  // ——— ceny: index k rovnakému obdobiu minulého roka a reťazový index od 1. Q 2022 ———
  let ceny: any = null;
  if (d?.ceny?.rad?.length) {
    const rad = d.ceny.rad;
    const p = rad[rad.length - 1];
    ceny = {
      zdroj: d.ceny.zdroj.nazov,
      obdobie: obdobie(p.obdobie),
      ba: p.ba_total_rr - 100,
      sr: p.sr_total_rr - 100,
      nove: p.ba_dw_new_rr != null ? p.ba_dw_new_rr - 100 : null,
      starsie: p.ba_dw_exst_rr != null ? p.ba_dw_exst_rr - 100 : null,
      od2022: p.ba_total_idx - 100,
      od2022sr: p.sr_total_idx - 100,
      // [obdobie, BA, SR, BA nové, BA staršie] – index 1. Q 2022 = 100
      rad: [['1. Q 2022', 100, 100, 100, 100], ...rad.map((r: any) => [obdobie(r.obdobie), r.ba_total_idx, r.sr_total_idx, r.ba_dw_new_idx, r.ba_dw_exst_idx])],
      rr: rad.map((r: any) => [obdobie(r.obdobie), +(r.ba_total_rr - 100).toFixed(1), +(r.sr_total_rr - 100).toFixed(1)]),
    };
  }

  // ——— výstavba bytov ———
  let vystavba: any = null;
  if (d?.vystavba?.roky) {
    const roky = Object.keys(d.vystavba.roky).sort();
    const rok = roky[roky.length - 1];
    const okresy = Object.keys(d.vystavba.okresy_casti);
    const desat = roky.slice(-10);
    vystavba = {
      zdroj: d.vystavba.zdroj.nazov,
      rok,
      rad: roky.map((r) => [r, d.vystavba.roky[r].Bratislava.DOKONC_BYT, d.vystavba.roky[r].Bratislava.ZAC_BYT ?? null]),
      posledny: d.vystavba.roky[rok].Bratislava,
      priemer10: Math.round(desat.reduce((s, r) => s + (d.vystavba.roky[r].Bratislava.DOKONC_BYT ?? 0), 0) / desat.length),
      okresy: okresy.map((o) => ({
        okres: o,
        casti: d.vystavba.okresy_casti[o],
        dokoncene: d.vystavba.roky[rok][o]?.DOKONC_BYT ?? 0,
        zacate: d.vystavba.roky[rok][o]?.ZAC_BYT ?? null,
        rozostavane: d.vystavba.roky[rok][o]?.ROZOST_BYT_KON ?? null,
        desatrocie: desat.reduce((s, r) => s + (d.vystavba.roky[r][o]?.DOKONC_BYT ?? 0), 0),
      })),
    };
  }

  // ——— byty hlavného mesta (nezverené mestským častiam) ———
  let mestske: any = null;
  const tm = tabulka('287e27b4174642369028a693db613320');
  if (tm?.riadky?.length) {
    const domy = tm.riadky.map((r: any[]) => [String(r[0]).trim(), cislo(r[1]) ?? 0] as [string, number]).filter(([, n]: [string, number]) => n > 0);
    mestske = {
      byty: domy.reduce((s: number, [, n]: [string, number]) => s + n, 0),
      domy: domy.length,
      k: (tm.stlpce[1]?.n ?? '').match(/\d{1,2}\.\d{1,2}\.\d{4}/)?.[0] ?? '',
      najvacsie: [...domy].sort((a, b) => b[1] - a[1]).slice(0, 6),
      url: tm.zdroj,
    };
  }

  // ——— komunitné bývanie ———
  let komunitne: any = null;
  const tk = tabulka('ed15579d1a65471187497a534b8de8f4');
  if (tk?.riadky?.length) {
    const i = (k: RegExp) => tk.stlpce.findIndex((s: any) => k.test(s.k) || k.test(s.n));
    const [iu, im, iv, ib] = [i(/ULICA/i), i(/MESTSKA|Mestská/i), i(/VYMERA|Výmera/i), i(/BYT|jednot/i)];
    komunitne = tk.riadky.map((r: any[]) => ({ ulica: r[iu], mc: r[im], vymera: cislo(r[iv]) ?? 0, byty: ib >= 0 ? cislo(r[ib]) : null }));
  }

  // ——— príspevok na bývanie podľa okresov (posledný rok) ———
  let prispevok: any = null;
  const tp = tabulka('ee14a168b11641639b14675a9ebd2c29');
  if (tp?.riadky?.length) {
    const io = tp.stlpce.findIndex((s: any) => s.k === 'Okres');
    const ir = tp.stlpce.findIndex((s: any) => s.k === 'Rok');
    const is = tp.stlpce.findIndex((s: any) => s.k === 'Spolu');
    const rok = Math.max(...tp.riadky.map((r: any[]) => Number(r[ir])).filter(Number.isFinite));
    const okresy = tp.riadky.filter((r: any[]) => Number(r[ir]) === rok && /Bratislava\s+[IV]+$/i.test(String(r[io]).trim()))
      .map((r: any[]) => [String(r[io]).trim().replace(/^Okres\s+/i, ''), cislo(r[is]) ?? r.slice(is + 1).reduce((a: number, x: unknown) => a + (cislo(x) ?? 0), 0)] as [string, number])
      .sort((a: [string, number], b: [string, number]) => a[0].localeCompare(b[0]));
    if (okresy.length) prispevok = { rok, okresy, spolu: okresy.reduce((s: number, [, n]: [string, number]) => s + n, 0) };
  }

  // ——— obývané byty podľa sčítania 2021 ———
  let fond: any = null;
  const sc = citaj('data', 'scitanie-bratislava.json');
  const bv = sc?.temy?.byty_vlastnictvo;
  if (bv?.mestske_casti) {
    const vlastne = (x: any) => (x['vlastný byt v bytovom dome'] ?? 0) + (x['byt vo vlastnom rodinnom dome'] ?? 0);
    const najom = (x: any) => (x['obecný byt'] ?? 0) + (x['byt v nájme'] ?? 0) + (x['služobný a domovnícky byt'] ?? 0) + (x['družstevný byt - len stavebné bytové družstvá'] ?? 0);
    fond = {
      spolu: bv.mesto.Spolu,
      vlastne: (vlastne(bv.mesto) / bv.mesto.Spolu) * 100,
      najom: (najom(bv.mesto) / bv.mesto.Spolu) * 100,
      obecne: bv.mesto['obecný byt'] ?? 0,
      casti: Object.entries<any>(bv.mestske_casti)
        .map(([mc, x]) => [mc, x.Spolu, +((vlastne(x) / x.Spolu) * 100).toFixed(1), +((najom(x) / x.Spolu) * 100).toFixed(1)])
        .sort((a: any, b: any) => b[1] - a[1]),
      zdroj: `${sc.zdroj.nazov}, obývané byty podľa formy vlastníctva (${bv.kocka})`,
    };
  }

  cache = { ceny, vystavba, mestske, komunitne, prispevok, fond };
  return cache;
}
