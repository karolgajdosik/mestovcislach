// Označenie verzie webu (jedno pre celý build) – stránka ho má v <html data-verzia>, /verzia.json vracia aktuálne nasadené.
// Keď sa líšia, stránka ponúkne „Obnoviť“ (Base.astro).
export const VERZIA = (process.env.CF_PAGES_COMMIT_SHA ?? '').slice(0, 12) || `b${Date.now().toString(36)}`;
