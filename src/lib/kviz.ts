// Kvíz „Poznáš svoje mesto?“ – otázky generované pri builde z dát webu (ŠÚ SR, voľby, školy, hospodárenie).
// Nesprávne možnosti sú odvodené deterministicky (rovnaký build = rovnaký kvíz).
import { citaj } from './adresa';
import { MESTA } from '../mesta';
import { obdobia, skrat } from './zastupitelstvo';
import { hospodarenie } from './mapa';

export type Otazka = { q: string; moznosti: string[]; spravna: number; vysvetlenie: string };

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
  const pridaj = (q: string, spravna: string, zle: string[], vysvetlenie: string) => {
    const z = zamiesaj(spravna, zle, `${slug}|${q}`);
    if (z.moznosti.length >= 3) ot.push({ q, ...z, vysvetlenie });
  };
  const naj = (k: string, max = true) => por.filter((x) => x[k] != null).sort((a, b) => (max ? b[k] - a[k] : a[k] - b[k]));

  if (ja?.obyvatelia) {
    const o = zaokr(ja.obyvatelia);
    pridaj(`Koľko obyvateľov má ${m.nazov}?`, `približne ${tis(o)}`, [0.55, 1.45, 2.1, 0.75].map((k) => `približne ${tis(zaokr(o * k))}`),
      `${m.nazov}: ${tis(ja.obyvatelia)} obyvateľov k 31. 12. ${ja.rok} (Štatistický úrad SR).`);
  }
  if (ja?.zmena10 != null) {
    const f = (x: number) => `${x > 0 ? 'pribudlo' : 'ubudlo'} asi ${des(Math.abs(x), 0)} %`;
    const v = ja.zmena10;
    pridaj(`Ako sa za posledných 10 rokov zmenil počet obyvateľov – ${m.nazov}?`, f(v), [f(-v || 3), f(v + (v > 0 ? 9 : -6)), f(v > 0 ? 2 : 1), f(v - 4)].filter((x) => x !== f(v)),
      `Za 10 rokov ${v > 0 ? 'pribudlo' : 'ubudlo'} ${des(Math.abs(v))} % obyvateľov. ${v < 0 ? 'Väčšina krajských miest sa zmenšuje – ľudia sa sťahujú do okolitých obcí.' : 'Rastie najmä vďaka novej výstavbe.'}`);
  }
  const vs = naj('vs');
  if (vs.length >= 4) pridaj('Ktoré krajské mesto má najvyšší podiel ľudí s vysokoškolským vzdelaním?', vs[0].nazov, vs.slice(1, 4).map((x) => x.nazov),
    `${vs[0].nazov} – ${des(vs[0].vs)} % obyvateľov nad 15 rokov má vysokoškolské vzdelanie (sčítanie 2021).${ja && vs[0].slug !== slug ? ` ${m.nazov}: ${des(ja.vs)} %.` : ''}`);
  if (ja?.pdu != null) {
    const v = ja.pdu;
    pridaj(`Aká je nezamestnanosť – ${m.nazov}?`, `${des(v)} %`, [v * 2.4, v * 3.6, v * 1.6].map((x) => `${des(x)} %`),
      `Podiel disponibilných uchádzačov o zamestnanie je ${des(v)} % (ÚPSVaR). Krajské mestá majú nezamestnanosť nižšiu ako slovenský priemer.`);
  }
  const sen = naj('seniori');
  if (sen.length >= 4) pridaj('V ktorom krajskom meste je najvyšší podiel seniorov (65+)?', sen[0].nazov, [sen[sen.length - 1], sen[3], sen[5] ?? sen[2]].map((x) => x.nazov),
    `${sen[0].nazov} – ${des(sen[0].seniori)} % obyvateľov má 65 a viac rokov.`);

  const ob = obdobia(slug).find((o) => !o.priebezne);
  if (ob) {
    const kom = slug === 'bratislava' ? citaj('data', 'komunalne-bratislava.json')?.volby?.find((v: any) => v.id === ob.rok)?.oso?.primator?.kandidati
      : citaj('data', 'mesta', `${slug}.json`)?.komunalne?.[ob.rok]?.primator;
    const kand = (kom ?? []).slice().sort((a: any, b: any) => b.hlasy - a.hlasy);
    if (ob.primator && kand.length >= 3) pridaj(`Kto vyhral voľbu primátora v roku ${ob.rok}?`, ob.primator.meno, kand.filter((k: any) => !k.zvoleny).map((k: any) => k.meno),
      `${ob.primator.meno} (${skrat(ob.primator.strany)}) získal(a) ${ob.primator.podiel != null ? des(ob.primator.podiel) + ' % hlasov' : 'najviac hlasov'}.`);
    if (ob.poslancov) pridaj(`Koľko poslancov má mestské zastupiteľstvo – ${m.nazov}?`, String(ob.poslancov), [ob.poslancov - 6, ob.poslancov + 4, ob.poslancov + 12, ob.poslancov - 10].filter((x) => x > 8).map(String),
      `${ob.poslancov} poslancov zvolených v roku ${ob.rok}. Počet určuje zastupiteľstvo podľa veľkosti mesta.`);
    if (ob.ucast != null) pridaj(`Aká bola účasť v komunálnych voľbách ${ob.rok}?`, `${des(ob.ucast, 0)} %`, [ob.ucast + 22, ob.ucast - 14, ob.ucast + 35].map((x) => `${des(x, 0)} %`),
      `Volilo ${des(ob.ucast)} % voličov – v komunálnych voľbách býva účasť výrazne nižšia ako v parlamentných.`);
  }

  const sk = citaj('data', 'mesta', 'skoly.json')?.mesta?.[slug];
  if (sk?.suhrn?.zs?.skol) {
    const n = sk.suhrn.zs.skol;
    pridaj(`Koľko základných škôl je v meste – ${m.nazov}?`, String(n), [Math.round(n * 0.5), Math.round(n * 1.7), Math.round(n * 2.6), Math.round(n * 0.7)].filter((x) => x > 2).map(String),
      `${n} základných škôl s ${tis(sk.suhrn.zs.ziakov)} žiakmi (Digitálna mapa škôl, MŠVVaM SR).`);
    const ss = (sk.skoly as any[]).filter((x) => x.t === 'ss' && x.z1 != null).sort((a, b) => b.z1 - a.z1);
    if (ss.length >= 6) pridaj('Ktorú strednú školu si pri prijímačkách dalo ako 1. voľbu najviac uchádzačov?', ss[0].n, [ss[ss.length - 1], ss[Math.floor(ss.length / 2)], ss[ss.length - 2]].map((x) => x.n),
      `${ss[0].n}: ${tis(ss[0].z1)} prihlášok s 1. voľbou (MŠVVaM SR).`);
  }

  const dane = MESTA.filter((x) => x.aktivne).map((x) => { const h = hospodarenie(x.slug); const o = por.find((y) => y.slug === x.slug)?.obyvatelia; return h && o ? { n: x.nazov, v: h.posledny.danove_vynosy / o } : null; })
    .filter(Boolean).sort((a: any, b: any) => b.v - a.v) as { n: string; v: number }[];
  if (dane.length >= 4) pridaj('Ktoré krajské mesto má najvyššie daňové výnosy na obyvateľa?', dane[0].n, [dane[dane.length - 1], dane[3], dane[5] ?? dane[2]].map((x) => x.n),
    `${dane[0].n} – asi ${tis(Math.round(dane[0].v))} € na obyvateľa ročne (účtovná závierka mesta). Pri Bratislave a Košiciach len mesto bez mestských častí, ktoré majú vlastné dane.`);
  return ot.slice(0, 10);
}
