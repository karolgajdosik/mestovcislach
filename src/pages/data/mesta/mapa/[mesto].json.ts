// Zlúčená mapa mesta pre klienta (/data/mesta/mapa/<slug>.json) – portál mesta + OpenStreetMap.
import { MESTA } from '../../../../mesta';
import { maMapu, mapaMesta } from '../../../../lib/mapa';

export function getStaticPaths() {
  return MESTA.filter((m) => m.aktivne && !m.plne && maMapu(m.slug)).map((m) => ({ params: { mesto: m.slug } }));
}

export function GET({ params }: { params: { mesto: string } }) {
  return new Response(JSON.stringify(mapaMesta(params.mesto)), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
