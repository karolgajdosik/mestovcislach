import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://mestovcislach.sk',
  // žiadne vložené (inline) skripty – Content-Security-Policy v public/_headers povoľuje len skripty z vlastnej domény
  vite: { build: { assetsInlineLimit: 0 } },
});
