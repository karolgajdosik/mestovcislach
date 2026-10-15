// Okná (popupy) pre vrstvy z celoštátnych registrov: pamiatky, školy, sociálne služby, chránené stromy, obvody ZŠ.
// Používajú rovnaké triedy .mf* ako popupMiesta (štýly v Base.astro).

const esc = (t: unknown) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);
const fmt = (n: number) => n.toLocaleString('sk-SK');
const odkaz = (url: string | undefined, text: string) => (url && /^https?:\/\//.test(url) ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text)}</a>` : '');
const obal = (r: (string | false | undefined | null)[]) => `<div class="mf">${r.filter(Boolean).join('')}</div>`;

export function popupPamiatky(nazov: string, d: any = {}): string {
  const opis = [d.vznik, d.sloh].filter(Boolean).join(' · ');
  return obal([
    `<strong class="mf-nazov">${esc(nazov)}</strong>`,
    `<span class="mf-kat">${esc(d.typ ?? 'Kultúrna pamiatka')}${d.celok ? ` · ${esc(d.celok)}` : ''}</span>`,
    d.a && `<span class="mf-adr">${esc(d.a)}${d.mc ? `, ${esc(d.mc)}` : ''}</span>`,
    opis && `<span>${esc(opis)}</span>`,
    d.obj?.length > 1 && `<span class="mf-hod">Objekty: ${d.obj.map(esc).join('; ')}</span>`,
    `<span class="mf-zdroj">Národná kultúrna pamiatka č. ÚZPF ${esc(d.uzpf)} · register MK SR</span>`,
  ]);
}

const TYPY_SKOL: Record<string, string> = { ms: 'Materská škola', zs: 'Základná škola', ss: 'Stredná škola', spec: 'Špeciálna škola', zus: 'Základná umelecká škola', cvc: 'Centrum voľného času' };
export function popupSkoly(nazov: string, typ: string, d: any = {}): string {
  const cisla = [d.z && `${fmt(d.z)} žiakov`, d.ped && `${fmt(d.ped)} pedagógov`].filter(Boolean).join(' · ');
  return obal([
    `<strong class="mf-nazov">${esc(nazov)}</strong>`,
    `<span class="mf-kat">${esc(TYPY_SKOL[typ] ?? 'Škola')}${d.jaz ? ` · ${esc(d.jaz)}` : ''}</span>`,
    d.a && `<span class="mf-adr">${esc(d.a)}</span>`,
    cisla && `<span>${cisla}</span>`,
    d.roz && `<span class="mf-hod">Rozpočet 2024: ${fmt(d.roz)} €</span>`,
    d.w && `<span class="mf-odkazy">${odkaz(d.w, 'Web školy')}</span>`,
    `<span class="mf-zdroj">Digitálna mapa škôl MŠVVaM SR</span>`,
  ]);
}

export function popupSocialne(nazov: string, kategoria: string, d: any = {}): string {
  return obal([
    `<strong class="mf-nazov">${esc(nazov)}</strong>`,
    `<span class="mf-kat">${esc(d.druh ?? kategoria)}</span>`,
    d.a && `<span class="mf-adr">${esc(d.a)}</span>`,
    (d.forma || d.kap) && `<span>${esc([d.forma, d.kap && `kapacita ${d.kap}`].filter(Boolean).join(' · '))}</span>`,
    d.pre && `<span class="mf-hod">Pre: ${esc(d.pre)}</span>`,
    d.posk && `<span class="mf-hod">${esc(d.posk)}</span>`,
    d.w && `<span class="mf-odkazy">${odkaz(d.w, 'Web')}</span>`,
    `<span class="mf-zdroj">Register poskytovateľov sociálnych služieb MPSVR SR</span>`,
  ]);
}

export function popupStromy(nazov: string, d: any = {}): string {
  return obal([
    `<strong class="mf-nazov">${esc(nazov)}</strong>`,
    `<span class="mf-kat">Chránený strom${d.druh ? ` · ${esc(d.druh)}` : ''}${d.pocet > 1 ? ` · ${d.pocet} stromov` : ''}</span>`,
    d.lok && `<span class="mf-adr">${esc(d.lok)}</span>`,
    d.dovod && `<span class="mf-hod">${esc(d.dovod)}</span>`,
    d.url && `<span class="mf-odkazy">${odkaz(d.url.replace(/^http:/, 'https:'), 'Štátny zoznam ŠOP SR')}</span>`,
  ]);
}

export function popupObvodu(p: any): string {
  return obal([
    `<strong class="mf-nazov">${esc(p.nazov)}</strong>`,
    `<span class="mf-kat">Spádový obvod základnej školy · ${esc(p.mc)}</span>`,
    p.adresa && `<span class="mf-adr">${esc(p.adresa)}</span>`,
    p.web && `<span class="mf-odkazy">${odkaz(p.web, /\.pdf$/i.test(p.web) ? 'Nariadenie o obvodoch' : 'Web školy')} · <a href="/vybavenost#spadova-skola">Hľadať podľa adresy</a></span>`,
    `<span class="mf-zdroj">Hranice sú približné – presne platí zoznam adries.</span>`,
  ]);
}
