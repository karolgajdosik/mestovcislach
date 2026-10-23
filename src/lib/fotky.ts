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
