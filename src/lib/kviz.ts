// Kvíz „Poznáš svoje mesto?“ – otázky generované pri builde z dát webu (ŠÚ SR, voľby, školy, hospodárenie).
// Nesprávne možnosti sú odvodené deterministicky (rovnaký build = rovnaký kvíz).
import { citaj } from './adresa';
import { MESTA } from '../mesta';
import { obdobia, skrat } from './zastupitelstvo';
import { hospodarenie } from './mapa';

export type Graf =
  | { typ: 'stlpce'; nadpis: string; jednotka?: string; des?: number; polozky: { n: string; v: number; ja?: boolean }[] }
  | { typ: 'ciara'; nadpis: string; roky: string[]; hodnoty: number[]; pozn?: string };
export type Otazka = { q: string; moznosti: string[]; spravna: number; vysvetlenie: string; tema: string; graf?: Graf };

// jednoduchý deterministický generátor (podľa textu otázky)
const nahoda = (seed: string) => {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) { h = Math.imul(h ^ seed.charCodeAt(i), 3432918353); h = (h << 13) | (h >>> 19); }
  let a = h >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
};
function zamiesaj(spravna: string, zle: string[], seed: string): { moznosti: string[]; spravna: number } {
  const r = nahoda(seed);
  const vsetky = [spravna, ...[...new Set(zle)].filter((z) => z !== spravna).slice(0, 3)];
  for (let i = vsetky.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [vsetky[i], vsetky[j]] = [vsetky[j], vsetky[i]]; }
  return { moznosti: vsetky, spravna: vsetky.indexOf(spravna) };
}
const tis = (n: number) => n.toLocaleString('sk-SK');
const des = (n: number, d = 1) => n.toLocaleString('sk-SK', { minimumFractionDigits: d, maximumFractionDigits: d });
const zaokr = (n: number) => { const r = 10 ** Math.max(0, Math.floor(Math.log10(n)) - 1); return Math.round(n / r) * r; };

export function kviz(slug: string): Otazka[] {
  const m = MESTA.find((x) => x.slug === slug)!;
  const por: any[] = citaj('data', 'mesta', 'porovnanie.json')?.mesta ?? [];
  const ja = por.find((x) => x.slug === slug);
  const ot: Otazka[] = [];
  const pridaj = (tema: string, q: string, spravna: string, zle: string[], vysvetlenie: string, graf?: Graf) => {
    const z = zamiesaj(spravna, zle, `${slug}|${q}`);
    if (z.moznosti.length >= 3) ot.push({ q, ...z, vysvetlenie, tema, ...(graf ? { graf } : {}) });
  };
  // stĺpce pre všetky krajské mestá (aktuálne mesto zvýraznené)
  const mesta = (k: string, nadpis: string, jednotka = '', d = 1, max = true): Graf => ({
    typ: 'stlpce', nadpis, jednotka, des: d,
    polozky: naj(k, max).map((x) => ({ n: x.nazov, v: x[k], ...(x.slug === slug ? { ja: true } : {}) })),
  });
  const naj = (k: string, max = true) => por.filter((x) => x[k] != null).sort((a, b) => (max ? b[k] - a[k] : a[k] - b[k]));

  if (ja?.obyvatelia) {
    const o = zaokr(ja.obyvatelia);
    pridaj('Obyvatelia', `Koľko obyvateľov má ${m.nazov}?`, `približne ${tis(o)}`, [0.55, 1.45, 2.1, 0.75].map((k) => `približne ${tis(zaokr(o * k))}`),
      `${m.nazov}: ${tis(ja.obyvatelia)} obyvateľov k 31. 12. ${ja.rok} (Štatistický úrad SR).`, mesta('obyvatelia', 'Obyvatelia krajských miest', '', 0));
  }
  if (ja?.zmena10 != null) {
    const f = (x: number) => `${x > 0 ? 'pribudlo' : 'ubudlo'} asi ${des(Math.abs(x), 0)} %`;
    const v = ja.zmena10;
    const rad = citaj('data', 'mesta', `${slug}.json`)?.obyvatelia?.roky ?? {};
    const roky = Object.keys(rad).sort().filter((r) => r >= '2012').slice(-14); // od 2012 – bez skoku po sčítaní 2011
    pridaj('Obyvatelia', `Ako sa za posledných 10 rokov zmenil počet obyvateľov – ${m.nazov}?`, f(v), [f(-v || 3), f(v + (v > 0 ? 9 : -6)), f(v > 0 ? 2 : 1), f(v - 4)].filter((x) => x !== f(v)),
      `Za 10 rokov ${v > 0 ? 'pribudlo' : 'ubudlo'} ${des(Math.abs(v))} % obyvateľov. ${v < 0 ? 'Väčšina krajských miest sa zmenšuje – ľudia sa sťahujú do okolitých obcí.' : 'Rastie najmä vďaka novej výstavbe.'}`,
      roky.length > 5 ? { typ: 'ciara', nadpis: `Počet obyvateľov ${roky[0]}–${roky.at(-1)}`, roky, hodnoty: roky.map((r) => rad[r]),
        ...(rad['2020'] && rad['2021'] && Math.abs(rad['2021'] / rad['2020'] - 1) > 0.012 ? { pozn: 'Skok v roku 2021 spôsobilo sčítanie obyvateľov – spresnilo, koľko ľudí v meste naozaj žije.' } : {}) } : mesta('zmena10', 'Zmena počtu obyvateľov za 10 rokov', ' %'));
  }
  const vs = naj('vs');
  if (vs.length >= 4) pridaj('Vzdelanie', 'Ktoré krajské mesto má najvyšší podiel ľudí s vysokoškolským vzdelaním?', vs[0].nazov, vs.slice(1, 4).map((x) => x.nazov),
    `${vs[0].nazov} – ${des(vs[0].vs)} % obyvateľov nad 15 rokov má vysokoškolské vzdelanie (sčítanie 2021).${ja && vs[0].slug !== slug ? ` ${m.nazov}: ${des(ja.vs)} %.` : ''}`, mesta('vs', 'Podiel ľudí s vysokoškolským vzdelaním', ' %'));
  if (ja?.pdu != null) {
    const v = ja.pdu;
    pridaj('Práca', `Aká je nezamestnanosť – ${m.nazov}?`, `${des(v)} %`, [v * 2.4, v * 3.6, v * 1.6].map((x) => `${des(x)} %`),
      `Podiel disponibilných uchádzačov o zamestnanie je ${des(v)} % (ÚPSVaR). Krajské mestá majú nezamestnanosť nižšiu ako slovenský priemer.`, mesta('pdu', 'Nezamestnanosť v krajských mestách', ' %', 2, false));
  }
  const sen = naj('seniori');
  if (sen.length >= 4) pridaj('Obyvatelia', 'V ktorom krajskom meste je najvyšší podiel seniorov (65+)?', sen[0].nazov, [sen[sen.length - 1], sen[3], sen[5] ?? sen[2]].map((x) => x.nazov),
    `${sen[0].nazov} – ${des(sen[0].seniori)} % obyvateľov má 65 a viac rokov.`, mesta('seniori', 'Podiel obyvateľov 65+', ' %'));

  const ob = obdobia(slug).find((o) => !o.priebezne);
  if (ob) {
    const kom = slug === 'bratislava' ? citaj('data', 'komunalne-bratislava.json')?.volby?.find((v: any) => v.id === ob.rok)?.oso?.primator?.kandidati
      : citaj('data', 'mesta', `${slug}.json`)?.komunalne?.[ob.rok]?.primator;
    const kand = (kom ?? []).slice().sort((a: any, b: any) => b.hlasy - a.hlasy);
    if (ob.primator && kand.length >= 3) pridaj('Voľby', `Kto vyhral voľbu primátora v roku ${ob.rok}?`, ob.primator.meno, kand.filter((k: any) => !k.zvoleny).map((k: any) => k.meno),
      `${ob.primator.meno} (${skrat(ob.primator.strany)}) získal(a) ${ob.primator.podiel != null ? des(ob.primator.podiel) + ' % hlasov' : 'najviac hlasov'}.`,
      kand[0].podiel != null ? { typ: 'stlpce', nadpis: `Voľba primátora ${ob.rok}`, jednotka: ' %', des: 1, polozky: kand.slice(0, 6).map((k: any) => ({ n: k.meno, v: k.podiel, ...(k.zvoleny ? { ja: true } : {}) })) } : undefined);
    if (ob.poslancov) pridaj('Voľby', `Koľko poslancov má mestské zastupiteľstvo – ${m.nazov}?`, String(ob.poslancov), [ob.poslancov - 6, ob.poslancov + 4, ob.poslancov + 12, ob.poslancov - 10].filter((x) => x > 8).map(String),
      `${ob.poslancov} poslancov zvolených v roku ${ob.rok}. Počet určuje zastupiteľstvo podľa veľkosti mesta.`,
      { typ: 'stlpce', nadpis: 'Zloženie zastupiteľstva', jednotka: '', des: 0, polozky: ob.mandaty.slice().sort((a, b) => b.mandaty - a.mandaty).slice(0, 7).map((x) => ({ n: skrat(x.strany), v: x.mandaty })) });
    if (ob.ucast != null) pridaj('Voľby', `Aká bola účasť v komunálnych voľbách ${ob.rok}?`, `${des(ob.ucast, 0)} %`, [ob.ucast + 22, ob.ucast - 14, ob.ucast + 35].map((x) => `${des(x, 0)} %`),
      `Volilo ${des(ob.ucast)} % voličov – v komunálnych voľbách býva účasť výrazne nižšia ako v parlamentných.`, mesta('ucast_komunalne', `Účasť v komunálnych voľbách ${ob.rok}`, ' %'));
  }

  const sk = citaj('data', 'mesta', 'skoly.json')?.mesta?.[slug];
  if (sk?.suhrn?.zs?.skol) {
    const n = sk.suhrn.zs.skol;
    const skVsetky = citaj('data', 'mesta', 'skoly.json')?.mesta ?? {};
    pridaj('Školy', `Koľko základných škôl je v meste – ${m.nazov}?`, String(n), [Math.round(n * 0.5), Math.round(n * 1.7), Math.round(n * 2.6), Math.round(n * 0.7)].filter((x) => x > 2).map(String),
      `${n} základných škôl s ${tis(sk.suhrn.zs.ziakov)} žiakmi (Digitálna mapa škôl, MŠVVaM SR).`,
      { typ: 'stlpce', nadpis: 'Základné školy v krajských mestách', des: 0, polozky: MESTA.filter((x) => skVsetky[x.slug]).map((x) => ({ n: x.nazov, v: skVsetky[x.slug].suhrn.zs.skol, ...(x.slug === slug ? { ja: true } : {}) })).sort((a, b) => b.v - a.v) });
    const ss = (sk.skoly as any[]).filter((x) => x.t === 'ss' && x.z1 != null).sort((a, b) => b.z1 - a.z1);
    if (ss.length >= 6) pridaj('Školy', 'Ktorú strednú školu si pri prijímačkách dalo ako 1. voľbu najviac uchádzačov?', ss[0].n, [ss[ss.length - 1], ss[Math.floor(ss.length / 2)], ss[ss.length - 2]].map((x) => x.n),
      `${ss[0].n}: ${tis(ss[0].z1)} prihlášok s 1. voľbou (MŠVVaM SR).`,
      { typ: 'stlpce', nadpis: 'Najviac prihlášok s 1. voľbou', des: 0, polozky: ss.slice(0, 6).map((x, i) => ({ n: x.n, v: x.z1, ...(i === 0 ? { ja: true } : {}) })) });
  }

  const dane = MESTA.filter((x) => x.aktivne).map((x) => { const h = hospodarenie(x.slug); const o = por.find((y) => y.slug === x.slug)?.obyvatelia; return h && o ? { n: x.nazov, v: h.posledny.danove_vynosy / o } : null; })
    .filter(Boolean).sort((a: any, b: any) => b.v - a.v) as { n: string; v: number }[];
  if (dane.length >= 4) pridaj('Peniaze', 'Ktoré krajské mesto má najvyššie daňové výnosy na obyvateľa?', dane[0].n, [dane[dane.length - 1], dane[3], dane[5] ?? dane[2]].map((x) => x.n),
    `${dane[0].n} – asi ${tis(Math.round(dane[0].v))} € na obyvateľa ročne (účtovná závierka mesta). Pri Bratislave a Košiciach len mesto bez mestských častí, ktoré majú vlastné dane.`,
    { typ: 'stlpce', nadpis: 'Daňové výnosy na obyvateľa', jednotka: ' €', des: 0, polozky: dane.map((x) => ({ n: x.n, v: Math.round(x.v), ...(x.n === m.nazov ? { ja: true } : {}) })) });
  return ot.slice(0, 10);
}
