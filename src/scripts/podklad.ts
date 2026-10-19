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

/** Prepínač podkladu Mapa / Snímka (letecká snímka Esri World Imagery + cesty a názvy) ako ovládač v pravom hornom rohu. */
export function prepinacPodkladu(mapa: L.Map, osm: L.TileLayer): void {
  const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/';
  if (!mapa.getPane('popisky')) {
    const p = mapa.createPane('popisky');
    p.style.zIndex = '450';
    p.style.pointerEvents = 'none';
  }
  const orto = L.layerGroup([
    L.tileLayer(`${ESRI}World_Imagery/MapServer/tile/{z}/{y}/{x}`, { maxZoom: 19, attribution: 'Snímky © Esri, Maxar, Earthstar Geographics' }),
    ...['Reference/World_Transportation', 'Reference/World_Boundaries_and_Places'].map((v) =>
      L.tileLayer(`${ESRI}${v}/MapServer/tile/{z}/{y}/{x}`, { maxZoom: 19, pane: 'popisky' })),
  ]);
  const Ovladac = L.Control.extend({
    onAdd() {
      const f = L.DomUtil.create('fieldset', 'podklad-prepinac');
      f.setAttribute('aria-label', 'Podklad mapy');
      f.innerHTML = '<label><input type="radio" name="podklad" value="mapa" checked><span>Mapa</span></label>'
        + '<label><input type="radio" name="podklad" value="orto"><span>Snímka</span></label>';
      L.DomEvent.disableClickPropagation(f);
      f.querySelectorAll<HTMLInputElement>('input').forEach((i) => i.addEventListener('change', () => {
        if (i.value === 'orto') { osm.remove(); orto.addTo(mapa); } else { orto.remove(); osm.addTo(mapa); }
      }));
      return f;
    },
  });
  new Ovladac({ position: 'topright' }).addTo(mapa);
}
