// Mapa stránok pre vyhľadávače: po zostavení prejde dist/ a zapíše dist/sitemap.xml (všetky HTML stránky).
// Volá sa z astro.config.mjs (hook astro:build:done), funguje teda pri akomkoľvek príkaze na build.
// Dôležitosť: úvod a prehľady miest najvyššie, katalóg datasetov najnižšie.
import fs from 'node:fs';
import path from 'node:path';

const WEB = 'https://mestovcislach.sk';
export function sitemap(DIST = path.resolve('dist')) {
const stranky = [];
(function prejdi(dir) {
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, f.name);
    if (f.isDirectory()) { if (!['_astro', 'data', 'og'].includes(f.name)) prejdi(p); }
    else if (f.name === 'index.html') stranky.push('/' + path.relative(DIST, path.dirname(p)).split(path.sep).filter(Boolean).map(encodeURIComponent).join('/'));
  }
})(DIST);

const priorita = (u) => {
  const c = u.split('/').filter(Boolean);
  if (c.length === 0) return '1.0';
  if (c.length === 1) return '0.9';
  if (c.includes('katalog') && c.length > 2) return '0.4';
  return c.length === 2 ? '0.8' : '0.6';
};
const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${stranky.sort().map((u) => `  <url><loc>${WEB}${u === '/' ? '/' : u + '/'}</loc><priority>${priorita(u)}</priority></url>`).join('\n')}
</urlset>
`;
fs.writeFileSync(path.join(DIST, 'sitemap.xml'), xml);
return stranky.length;
}

if (import.meta.url === `file://${process.argv[1]}`) console.log(`sitemap.xml: ${sitemap()} stránok`);
