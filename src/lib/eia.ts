// Kategórie zámerov v posudzovaní EIA/SEA (scripts/zber_eia.py): kľúč → [názov, farba svetlá, farba tmavá]
export const KATEGORIE_EIA: Record<string, [string, string, string]> = {
  byvanie: ['Bývanie a polyfunkcia', '#c8102e', '#ff6b80'],
  obcianska: ['Obchod, kancelárie, služby', '#7a4fd1', '#b79cff'],
  doprava: ['Doprava', '#1f6fd1', '#7cc4ff'],
  priemysel: ['Priemysel a sklady', '#a16207', '#fcd34d'],
  odpady: ['Odpady', '#57534e', '#d6d3d1'],
  energia: ['Energetika', '#d97706', '#fdba74'],
  voda: ['Voda a kanalizácia', '#0e7490', '#67e8f9'],
  plan: ['Územné plány a koncepcie', '#138a5e', '#4ade80'],
  ine: ['Iné', '#6b7280', '#9ca3af'],
};

export const slug = (mc: string) => mc.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, '-');
