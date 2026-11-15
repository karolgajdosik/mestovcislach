// Spustí fn, až keď je prvok blízko obrazovky – ťažké knižnice (grafy, mapy) sa tak sťahujú len keď treba.
export function kedViditelne(el: Element, fn: () => void, okraj = '400px'): void {
  if (!('IntersectionObserver' in window)) { fn(); return; }
  const io = new IntersectionObserver((e) => { if (e.some((x) => x.isIntersecting)) { io.disconnect(); fn(); } }, { rootMargin: okraj });
  io.observe(el);
}

/** Chart.js načítaný až na požiadanie (vlastný balík ~200 kB). */
export const nacitajChart = () => import('chart.js/auto').then((m) => m.default);
