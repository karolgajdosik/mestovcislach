// Ľahký preklad textov ovládania. Slovník (~30 kB) sa načíta len pri inom jazyku ako slovenčina –
// nahrá ho scripts/preklad.ts (window.__slovnik). Pri slovenčine tr() vracia text bez zmeny.
export const jazyk = (): string => document.documentElement.lang || 'sk';

export function tr(text: string): string {
  const s = (window as any).__slovnik as { SLOVNIK: Record<string, string[]>; PORADIE: readonly string[] } | undefined;
  if (!s) return text;
  const i = s.PORADIE.indexOf(jazyk());
  return i < 0 ? text : s.SLOVNIK[text.trim()]?.[i] ?? text;
}
