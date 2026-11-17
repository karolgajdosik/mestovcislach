// Údaje pre komponent PozriObec (video „… v číslach“ a 3D prelet) z obecných dát – pre stránky krajských miest a mestských častí.
import type { Snimka, VideoData } from '../scripts/video-obce';
import { ukazovatele } from './ukazovatele-obci';
import { klimaInfo, obrazkyInfo, wikiInfo, pamiatkyInfo, pamiatkyPreletu, kodyCasti, type PamiatkaPreletu } from './obce';

const des = (x: number, d = 1) => x.toLocaleString('sk-SK', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmt = (x: number) => Math.round(x).toLocaleString('sk-SK');
const zn = (x: number) => (x > 0 ? '+' : x < 0 ? '−' : '');
export type Prelet = { stred: [number, number]; bbox?: [number, number, number, number] | null; km2?: number | null; titulky: [string, string][]; pamiatky?: PamiatkaPreletu[] };

/** Video a prelet pre obec/mesto podľa kódu obce ŠÚ SR. */
export function videoObce(kod: string, url: string, kicker = 'v číslach'): { video: VideoData; prelet: Prelet | null } | null {
  const u = ukazovatele().find((x) => x.o.kod === kod);
  if (!u) return null;
  const { o, h } = u;
  const kli = (klimaInfo() as any)?.obce?.[kod] as number[] | undefined;
  const obr = (obrazkyInfo() as any)?.obce?.[kod];
  const wk = (wikiInfo() as any)?.obce?.[kod];
  const pam = (pamiatkyInfo() as any)?.obce?.[kod];
  const rad = Object.entries(o.obyvatelia).sort(([a], [b]) => a.localeCompare(b)).map(([, x]) => x as number).slice(-25);
  const sn: Snimka[] = [{ typ: 'titul', kicker, nadpis: o.nazov, pod: `okres ${o.okres} · ${u.kraj}` }];
  if (h.obyv != null) sn.push({ typ: 'cislo', hodnota: h.obyv, popis: 'Obyvatelia', pozn: h.z10 != null ? `${zn(h.z10)}${des(Math.abs(h.z10))} % za posledných 10 rokov` : undefined, rad });
  if (h.deti != null && h.sen != null) sn.push({ typ: 'stlpce', nadpis: 'Vek obyvateľov (sčítanie 2021)', polozky: [['Deti do 14 rokov', h.deti, `${des(h.deti)} %`], ['15 – 64 rokov', 100 - h.deti - h.sen, `${des(100 - h.deti - h.sen)} %`], ['65 a viac rokov', h.sen, `${des(h.sen)} %`]] });
  if (h.vek != null && h.vs != null) sn.push({ typ: 'dve', a: [`${des(h.vek)} r.`, 'priemerný vek'], b: [`${des(h.vs)} %`, 'ľudí s vysokou školou'] });
  if (kli) sn.push({ typ: 'dve', nadpis: `Podnebie ${(klimaInfo() as any)?.obdobie ?? ''}`, a: [`${des(kli[0])} °C`, 'priemerná ročná teplota'], b: [`${fmt(kli[1])} mm`, 'zrážok za rok'] });
  if (h.uc != null || h.nez != null) sn.push({ typ: 'dve', a: [h.uc != null ? `${des(h.uc)} %` : '–', 'účasť v komunálnych voľbách 2026'], b: [h.nez != null ? `${des(h.nez)} %` : '–', 'miera nezamestnanosti'] });
  sn.push({ typ: 'outro', nadpis: `${o.nazov} – všetky čísla`, url: `mestovcislach.sk${url}` });
  const titulky: [string, string][] = [[o.nazov, `okres ${o.okres} · ${u.kraj}`]];
  if (h.obyv != null) titulky.push([`${fmt(h.obyv)} obyvateľov`, h.z10 != null ? `${zn(h.z10)}${des(Math.abs(h.z10))} % za 10 rokov` : '']);
  if (wk?.[1]) titulky.push([`${fmt(wk[1])} m n. m.`, wk[0] ? `prvá písomná zmienka ${wk[0]}` : 'nadmorská výška']);
  if (pam?.n) titulky.push([`${fmt(pam.n)} pamiatok`, (pam.top ?? []).slice(0, 2).join(', ')]);
  if (h.vek != null) titulky.push([`Priemerný vek ${des(h.vek)} r.`, h.nez != null ? `nezamestnanosť ${des(h.nez)} %` : '']);
  titulky.push([o.nazov, 'Ďalšie čísla nájdete nižšie na stránke']);
  const km2 = h.hus && h.obyv ? h.obyv / h.hus : null;
  return {
    video: { nazov: o.nazov, slug: o.slug, foto: obr?.foto?.u ?? null, snimky: sn },
    prelet: o.poloha ? { stred: o.poloha as [number, number], bbox: null, km2, titulky, pamiatky: pamiatkyMesta(kod, url) } : null,
  };
}

/** Pamiatky mesta: z kódu mesta, a ak ich je málo, doplnené z mestských častí (Bratislava, Košice). */
function pamiatkyMesta(kod: string, url: string): PamiatkaPreletu[] {
  const vlastne = pamiatkyPreletu(kod);
  if (vlastne.length >= 4) return vlastne;
  const slug = url.replace(/^\//, '').split('/')[0];
  return pamiatkyPreletu(kod, ...Object.values(kodyCasti(slug)));
}

/** Video pre mestskú časť zo zadaných čísel (stránky mestských častí majú vlastné profily). */
export function videoCasti(a: { nazov: string; mesto: string; slug: string; url: string; obyv: number | null; rad: number[]; z10: number | null; deti: number | null; sen: number | null; vs: number | null; druhe?: [string, string] | null; ucast: number | null; nez?: number | null }): VideoData {
  const sn: Snimka[] = [{ typ: 'titul', kicker: 'mestská časť v číslach', nadpis: a.nazov, pod: a.mesto }];
  if (a.obyv != null) sn.push({ typ: 'cislo', hodnota: a.obyv, popis: 'Obyvatelia', pozn: a.z10 != null ? `${zn(a.z10)}${des(Math.abs(a.z10))} % za posledných 10 rokov` : undefined, rad: a.rad.slice(-25) });
  if (a.deti != null && a.sen != null) sn.push({ typ: 'stlpce', nadpis: 'Vek obyvateľov (sčítanie 2021)', polozky: [['Deti do 14 rokov', a.deti, `${des(a.deti)} %`], ['15 – 64 rokov', 100 - a.deti - a.sen, `${des(100 - a.deti - a.sen)} %`], ['65 a viac rokov', a.sen, `${des(a.sen)} %`]] });
  if (a.vs != null) sn.push({ typ: 'dve', a: [`${des(a.vs)} %`, 'ľudí s vysokou školou'], b: a.druhe ?? ['–', ''] });
  if (a.ucast != null || a.nez != null) sn.push({ typ: 'dve', a: [a.ucast != null ? `${des(a.ucast)} %` : '–', 'účasť v komunálnych voľbách 2026'], b: [a.nez != null ? `${des(a.nez)} %` : '–', a.nez != null ? 'nezamestnanosť (okres)' : ''] });
  sn.push({ typ: 'outro', nadpis: `${a.nazov} – všetky čísla`, url: `mestovcislach.sk${a.url}` });
  return { nazov: a.nazov, slug: a.slug, foto: null, snimky: sn };
}
