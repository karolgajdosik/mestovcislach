# mestovcislach.sk – pokyny pre Claude (aj pre automatických agentov)

Otvorené dáta o slovenských mestách a obciach. Odpovedaj a píš po slovensky.

## Technika
- Astro (statický web) + Cloudflare Pages (build z Git po každom pushe do `main`). Build `npm run build` trvá ~6 min, vytvorí ~17 400 súborov.
- **Limit Cloudflare Pages je 20 000 súborov** – nepridávaj nové súbory na každú obec. Nové funkcie riešiť jedným súborom / klientskym načítaním.
- Dáta: `data/` (JSON), zber cez Python skripty v `scripts/` a GitHub Actions v `.github/workflows/`. Spoločné pomôcky: `scripts/spolocne.py`.
- CSP je v `public/_headers` – nové externé zdroje treba doplniť do `connect-src` / `img-src`.
- Workflow „Kontrola webu“ (`kontrola.yml`) každé 3 hodiny overuje živé zdroje a úspešnosť zberov; pri probléme vedie issue „Kontrola webu“.
- Projektové poznámky sú v claude.ai projekte „Mestovcislach“ (nie v repozitári).

## Záväzné pravidlá
- **GDPR**: nikdy nezverejňovať osobné ani kontaktné údaje fyzických osôb. Dodávatelia bez IČO alebo fyzické osoby sa skryjú alebo sa len spočítajú. Pri poslancoch a kandidátoch len meno, strana/klub a hlasy. Texty podnetov občanov sa nezverejňujú.
- Stránka o ochrane súkromia: prevádzkovateľ je spoločnosť IT Future s.r.o., kontakt info@mestovcislach.sk – meno majiteľa (fyzickej osoby) sa nezverejňuje.
- Vetva `diag` je verejná: diagnostické výstupy nikdy nesmú obsahovať osobné údaje (mená, adresy fyzických osôb) – len počty, typy a názvy firiem či inštitúcií.
- E-mailové adresy odberateľov nikdy nesmú byť v repozitári ani v logoch (sú len v Brevo). Kľúč `BREVO_API_KEY` je len v secrets.
- Neobchádzať captcha ani iné ochrany zdrojov.
- Keď je zdroj nespoľahlivý alebo neúplný, nepublikovať polovičné dáta – nahlásiť to.
- User-Agent pri zbere: „mestovcislach.sk (info@mestovcislach.sk)“ alebo všeobecný názov – nikdy osobný e-mail.
- Commity končia riadkom `Co-Authored-By: Claude <noreply@anthropic.com>` (agent môže doplniť odkaz na reláciu).
- Veľké zmeny webu, mazanie dát alebo zmeny vzhľadu: pripraviť ako pull request na schválenie, nie priamo do `main`.
