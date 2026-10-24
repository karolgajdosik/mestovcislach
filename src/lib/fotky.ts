// Fotografie krajských miest (Wikimedia Commons, voľné licencie) – public/img/mesta/<slug>-{1600,800,480}.webp.
// Autori a licencie: src/lib/fotky-kredity.json (stiahnuté z Commons API). Licencie CC BY/BY-SA vyžadujú uvedenie autora.
import kredity from './fotky-kredity.json';

export type Foto = { src: string; srcset: string; autor: string; licencia: string; licenciaUrl?: string; zdroj: string };

export function foto(slug: string): Foto | null {
  const k = (kredity as Record<string, any>)[slug];
  if (!k) return null;
  const c = (w: number) => `/img/mesta/${slug}-${w}.webp`;
  return { src: c(800), srcset: `${c(480)} 480w, ${c(800)} 800w, ${c(1600)} 1600w`, autor: k.autor, licencia: k.licencia, licenciaUrl: k.licencia_url ?? undefined, zdroj: k.zdroj };
}

/** Ktorá fotka patrí na podstránku (pás navrchu); null = bez fotky (prehľady majú veľkú hlavičku, mapy celú plochu). */
export function fotoPreStranku(cesta: string): { kluc: string; popis: string } | null {
  const c = cesta.split('/').filter(Boolean);
  if (c.length !== 2) return null; // len hlavné podstránky mesta: /<mesto>/<sekcia>
  const [mesto, sekcia] = c;
  const BA: Record<string, [string, string]> = {
    'mestske-casti': ['bratislava-obyvatelia', 'Bratislava z výšky – Dunaj a mesto'],
    obyvatelia: ['bratislava-obyvatelia', 'Bratislava z výšky – Dunaj a mesto'],
    volby: ['bratislava-radnica', 'Primaciálny palác – sídlo hlavného mesta'],
    financie: ['bratislava-radnica', 'Primaciálny palác – sídlo hlavného mesta'],
    doprava: ['bratislava-doprava', 'Električka v Bratislave'],
    vystavba: ['bratislava-vystavba', 'Nové výškové budovy pri Dunaji'],
    prostredie: ['bratislava-prostredie', 'Park pri Dunaji s výhľadom na hrad'],
    vybavenost: ['bratislava', 'Bratislava – panoráma s hradom'],
    bezpecnost: ['bratislava', 'Bratislava – panoráma s hradom'],
  };
  const INE: Record<string, [string, string]> = {
    zivot: [`${mesto}-zivot`, 'Život v meste'],
    samosprava: [`${mesto}-radnica`, 'Radnica mesta'],
    volby: [`${mesto}-radnica`, 'Radnica mesta'],
  };
  const vyber = (mesto === 'bratislava' ? BA[sekcia] : undefined) ?? INE[sekcia] ?? (['adresa', 'upozornenia', 'katalog'].includes(sekcia) ? [mesto, 'Pohľad na mesto'] : null);
  return vyber && foto(vyber[0]) ? { kluc: vyber[0], popis: vyber[1] } : null;
}
