// Zobrazenie (režim, písmo, slabozrakí) pred vykreslením – bez bliknutia; voľbu mení Zobrazenie.astro
(function () {
  var d = document.documentElement, v = {};
  try { v = JSON.parse(localStorage.getItem('zobrazenie') || '{}'); } catch (e) {}
  // jazyk: ?lang=xx v odkaze má prednosť, inak uložená voľba
  var J = ['sk', 'en', 'de', 'pl', 'hu'], l = null;
  try { l = new URLSearchParams(location.search).get('lang'); } catch (e) {}
  if (l && J.indexOf(l) >= 0) { try { localStorage.setItem('jazyk', l); } catch (e) {} }
  else { try { l = localStorage.getItem('jazyk'); } catch (e) {} }
  if (!l || J.indexOf(l) < 0) l = 'sk';
  d.lang = l;
  if (l !== 'sk') d.className += ' prekladam';
  // graf vložený na iný web (/vlozit/…, functions/vlozit) – bez hlavičky, menu a pätičky
  if (d.getAttribute('data-vlozit')) d.className += ' vlozene';
  var tmava = v.tema === 'tmava' || (v.tema !== 'svetla' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  d.setAttribute('data-tema', tmava ? 'tmava' : 'svetla');
  if (v.slabozraky) d.setAttribute('data-slabozraky', '1');
  var p = (v.pismo || 100) * (v.slabozraky ? 1.2 : 1);
  if (p !== 100) d.style.fontSize = p + '%';
})();
