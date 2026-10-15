import L from 'leaflet';

// Podkladová mapa z OpenStreetMap (bez API kľúča). Vzhľad (sivá, tmavý režim)
// sa ladí cez CSS triedu .podklad-osm v Base.astro, aby vynikli údaje na mape.
export function osmPodklad(): L.TileLayer {
  return L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    className: 'podklad-osm',
    attribution: '© <a href="https://www.openstreetmap.org/copyright">prispievatelia OpenStreetMap</a>',
  });
}
