import { defineConfig } from 'astro/config';
import { fileURLToPath } from 'node:url';
import { sitemap } from './scripts/sitemap.mjs';

export default defineConfig({
  site: 'https://mestovcislach.sk',
  // žiadne vložené (inline) skripty – Content-Security-Policy v public/_headers povoľuje len skripty z vlastnej domény
  vite: { build: { assetsInlineLimit: 0 } },
  integrations: [{
    name: 'mapa-stranok',
    hooks: { 'astro:build:done': ({ dir, logger }) => logger.info(`sitemap.xml: ${sitemap(fileURLToPath(dir))} stránok`) },
  }],
});
