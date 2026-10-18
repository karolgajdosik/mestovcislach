import L from 'leaflet';

// Tlačidlo „Pri mne“ na mapách: poloha z prehliadača (Geolocation API) – neodosiela sa na server, len sa posunie mapa.
// Odkaz s #pri-mne (karta na prehľade mesta) poprosí o polohu hneď po otvorení mapy.
export function priMne(mapa: L.Map) {
  let znacka: L.LayerGroup | null = null;
  const sprava = (text: string) => L.popup({ closeButton: true, autoClose: true }).setLatLng(mapa.getCenter()).setContent(text).openOn(mapa);
  const najdi = () => {
    if (!('geolocation' in navigator)) { sprava('Prehliadač nepodporuje zistenie polohy.'); return; }
    tlacidlo.classList.add('hlada');
    navigator.geolocation.getCurrentPosition(
      (p) => {
        tlacidlo.classList.remove('hlada');
        const ll: L.LatLngExpression = [p.coords.latitude, p.coords.longitude];
        znacka?.remove();
        znacka = L.layerGroup([
          L.circle(ll, { radius: Math.min(p.coords.accuracy, 500), weight: 1, color: '#2563eb', fillOpacity: 0.08, interactive: false }),
          L.circleMarker(ll, { radius: 7, weight: 3, color: '#fff', fillColor: '#2563eb', fillOpacity: 1 }).bindTooltip('Ste tu'),
        ]).addTo(mapa);
        mapa.stop();
        mapa.setView(ll, 16, { animate: false });
      },
      (e) => {
        tlacidlo.classList.remove('hlada');
        sprava(e.code === e.PERMISSION_DENIED ? 'Poloha nie je povolená. Povoľte ju v nastaveniach prehliadača pre túto stránku.' : 'Polohu sa nepodarilo zistiť.');
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
    );
  };
  const Ovladac = L.Control.extend({
    onAdd() {
      const b = L.DomUtil.create('button', 'pri-mne leaflet-bar');
      b.type = 'button';
      b.title = 'Ukázať moju polohu';
      b.setAttribute('aria-label', 'Pri mne – ukázať moju polohu na mape');
      b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.2"/><circle cx="12" cy="12" r="7"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3"/></svg><span>Pri mne</span>';
      L.DomEvent.disableClickPropagation(b);
      b.addEventListener('click', najdi);
      return b;
    },
  });
  const tlacidlo = new Ovladac({ position: 'topleft' }).addTo(mapa).getContainer()!;
  // pri odkaze #pri-mne až po úvodnom priblížení na mesto (inak by animácia fitBounds prebila posun na polohu)
  if (/(^|[#&])pri-mne(&|$)/.test(location.hash)) setTimeout(najdi, 500);
}
