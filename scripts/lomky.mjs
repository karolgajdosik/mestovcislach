// Interné odkazy s lomkou na konci: Cloudflare Pages presmeruje /mesto/volby → /mesto/volby/ (308) a Google takéto
// adresy hlási ako „Stránka s presmerovaním“. Po zostavení prepíše v HTML href="/cesta" na href="/cesta/" –
// len ak dist/cesta/index.html existuje (súbory .xml, .ics, .json a funkcie /api ostanú bez zmeny).
import fs from 'node:fs';
import path from 'node:path';

export function lomky(DIST = path.resolve('dist')) {
  const jeStranka = new Map();
  const stranka = (cesta) => {
    if (!jeStranka.has(cesta)) {
      let c = cesta;
      try { c = decodeURIComponent(cesta); } catch { /* ponechať */ }
      jeStranka.set(cesta, fs.existsSync(path.join(DIST, c, 'index.html')));
    }
    return jeStranka.get(cesta);
  };
  let suborov = 0, zmien = 0;
  (function prejdi(dir) {
    for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, f.name);
      if (f.isDirectory()) { if (!['_astro', 'data', 'og'].includes(f.name)) prejdi(p); continue; }
      if (!f.name.endsWith('.html')) continue;
      const html = fs.readFileSync(p, 'utf-8');
      const nove = html.replace(/href="(\/[^"#?]*[^"#?/])([#?][^"]*)?"/g, (cela, cesta, zvysok = '') => {
        if (/\.[a-z0-9]{2,5}$/i.test(cesta) || !stranka(cesta)) return cela;
        zmien++;
        return `href="${cesta}/${zvysok}"`;
      });
      if (nove !== html) { fs.writeFileSync(p, nove); suborov++; }
    }
  })(DIST);
  return `${zmien} odkazov v ${suborov} súboroch`;
}
