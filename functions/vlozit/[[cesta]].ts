// Graf na vloženie do iného webu: /vlozit/<stránka>?g=<id sekcie> vráti tú istú statickú stránku,
// ale povolí jej zobrazenie v iframe (inak X-Frame-Options: DENY) a označí ju ako vloženú –
// skript na stránke potom ukáže len danú sekciu s grafom a odkaz na zdroj.
export const onRequestGet = async ({ request, env, params }: any) => {
  const url = new URL(request.url);
  const cesta = (Array.isArray(params.cesta) ? params.cesta : [params.cesta ?? '']).filter(Boolean).join('/');
  const g = (url.searchParams.get('g') ?? '').replace(/[^a-z0-9-]/gi, '').slice(0, 80);
  if (!g || /^(api|data|vlozit|_astro)\b/.test(cesta)) return new Response('Nenájdené', { status: 404 });
  const zdroj = await env.ASSETS.fetch(new URL(`/${cesta}${cesta ? '/' : ''}`, url));
  if (!zdroj.ok || !(zdroj.headers.get('content-type') ?? '').includes('text/html')) return new Response('Nenájdené', { status: 404 });
  const h = new Headers(zdroj.headers);
  h.delete('X-Frame-Options');
  const csp = h.get('Content-Security-Policy');
  if (csp) h.set('Content-Security-Policy', csp.replace(/frame-ancestors [^;]+/, 'frame-ancestors *'));
  h.set('X-Robots-Tag', 'noindex');
  h.set('Cache-Control', 'public, max-age=600');
  return new HTMLRewriter()
    .on('html', { element: (el: any) => el.setAttribute('data-vlozit', g) })
    .on('head', { element: (el: any) => el.append('<base target="_top">', { html: true }) })
    .transform(new Response(zdroj.body, { status: 200, headers: h }));
};
