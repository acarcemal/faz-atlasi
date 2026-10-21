'use strict';
/* Üst çubuktaki TR | EN seçici (dil.js'teki dilDegistir'i kullanır) */
document.querySelectorAll('.dil-sec [data-dil]').forEach((b) => {
  const secili = b.dataset.dil === DIL;
  b.classList.toggle('aktif', secili);
  b.setAttribute('aria-pressed', secili);
  b.addEventListener('click', () => dilDegistir(b.dataset.dil));
});
