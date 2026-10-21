'use strict';
/* Sabitlenen noktalar.
   Shift+tık: nokta sabitle · sabit noktanın üstüne gel: bilgi kartı · tık: turuncu nokta oraya gider
   Sağ tık: sabit noktayı sil. Noktalar diyagram kaynağına bağlıdır (ikili Fe–C ya da çelik kesiti)
   ve bu tarayıcıda hatırlanır. */

const PIN_ANAHTAR = 'fec-pinler-v1';
st.pinler = (() => {
  try {
    const l = JSON.parse(localStorage.getItem(PIN_ANAHTAR));
    return Array.isArray(l) ? l.filter((p) => p && isFinite(p.w) && isFinite(p.T) && typeof p.kaynak === 'string') : [];
  } catch (e) { return []; }
})();
st.pinUstunde = null;

const kaynakAnahtari = () => (KAYNAK.alt ? 'kesit:' + KAYNAK.alt.anahtar : 'ikili');
const gorunenPinler = () => st.pinler.filter((p) => p.kaynak === kaynakAnahtari());
function pinKaydet() {
  try { localStorage.setItem(PIN_ANAHTAR, JSON.stringify(st.pinler)); } catch (e) { /* gizli pencere vb. */ }
}
function pinNo(p) { return gorunenPinler().indexOf(p) + 1; }

function pinEkle(w, T) {
  st.pinler.push({ id: Date.now() + Math.random(), w, T, kaynak: kaynakAnahtari() });
  pinKaydet(); pinAraclari(); guncelle();
}
function pinSil(p) {
  st.pinler = st.pinler.filter((q) => q !== p);
  if (st.pinUstunde === p) { st.pinUstunde = null; kartGizle(); }
  pinKaydet(); pinAraclari(); guncelle();
}
function yakindakiPin(px, py) {
  let en = null, ed = 11;
  for (const p of gorunenPinler()) {
    const d = Math.hypot(sx(p.w) - px, sy(p.T) - py);
    if (d < ed) { ed = d; en = p; }
  }
  return en;
}

/* ---------- etkileşim kancaları ---------- */
KANCA.tik.push((e, w, T, px, py) => {
  const p = yakindakiPin(px, py);
  if (e.shiftKey) { if (!p) pinEkle(w, T); return true; }
  if (p) { sec(p.w, p.T); return true; }   // sabit noktaya tıklamak turuncu noktayı oraya taşır
  return false;
});
KANCA.sagTik.push((px, py) => {
  const p = yakindakiPin(px, py);
  if (p) { pinSil(p); return true; }
  return false;
});
KANCA.uzerinde.push((px, py) => {
  const p = px < 0 ? null : yakindakiPin(px, py);
  if (p !== st.pinUstunde) { st.pinUstunde = p; if (!p) kartGizle(); }
  if (p) kartGoster(p, px, py);
  return !!p;
});

/* ---------- çizim ---------- */
KANCA.ust.push(() => {
  const g = el('g', { 'clip-path': 'url(#kirp)' }, svg);
  for (const p of gorunenPinler()) {
    const x = sx(p.w), y = sy(p.T), aktif = p === st.pinUstunde;
    el('circle', { cx: x, cy: y, r: aktif ? 10 : 8.5, class: 'pin' + (aktif ? ' aktif' : '') }, g);
    el('text', { x, y: y + 0.5, class: 'pin-no' }, g).textContent = pinNo(p);
  }
});

/* ---------- bilgi kartı ---------- */
const kart = document.getElementById('pinKart');
function kartGizle() { kart.hidden = true; }

function noktaVerisi(w, T) {
  if (KAYNAK.alt) {
    const { r, fazlar } = KAYNAK.alt.oranlar(w, T);
    const k = KAYNAK.alt.kritik(w);
    return { r, fazlar, kritik: [['Ae1', k.ae1], [k.hipo ? 'Ae3' : t('kare.A1ustu'), k.ae3], ['Aecm', k.hipo ? null : k.aecm]] };
  }
  const d = durum(w, T);
  const gs = gecisler(w), bul = (kod) => { const g = gs.find((x) => x.kod === kod); return g ? g.T : null; };
  return { r: d.r, fazlar: d.fazlar, kritik: [['A1', bul('A1')], ['A3', bul('A3')], ['Acm', bul('Acm')]] };
}

function kartGoster(p, px, py) {
  const v = noktaVerisi(p.w, p.T);
  const fazSatir = v.fazlar.map((f) => `
    <div class="pk-faz">
      <i style="background:var(--ph-${f.f})"></i><span>${FAZ[f.f].kisa}</span>
      <span class="pk-cubuk"><b style="width:${(f.oran * 100).toFixed(1)}%;background:var(--ph-${f.f})"></b></span>
      <span class="pk-oran">${fmtP(f.oran)}</span>
      <span class="pk-c">${f.w != null ? fmtC(f.w) + ' C' : ''}</span>
    </div>`).join('');
  const kritik = v.kritik.filter(([, T]) => T != null).map(([ad, T]) => `<span><small>${ad}</small> ${fmt(T, 0)} °C</span>`).join('');
  let islem = '';
  if (st.detay && typeof islemAraliklari === 'function') {
    const r = islemAraliklari(p.w);
    const ar = (t) => (t ? `${fmt(t[0], 0)}–${fmt(t[1], 0)} °C` : '—');
    islem = `<div class="pk-satir"><span><small>${t('pin.sertlestirme')}</small> ${ar(r.tavlama)}</span><span><small>${t('bant.normal')}</small> ${ar(r.normal)}</span></div>`;
  }
  const dC = p.w - st.C, dT = p.T - st.T;
  const isaret = (x) => (x > 0 ? '+' : x < 0 ? '−' : '±');
  kart.innerHTML = `
    <div class="pk-baslik"><span class="pk-no">${pinNo(p)}</span><b>${fmtC(p.w)} C · ${fmtT(p.T)}</b>
      <small>${KAYNAK.alt ? t('pin.kesit', { ad: esc(KAYNAK.alt.ad) }) : 'Fe–C'}</small></div>
    <div class="pk-bolge">${kisaAd(v.r.p)}</div>
    ${fazSatir}
    <div class="pk-satir">${kritik}</div>
    ${islem}
    <div class="pk-alt">${t('pin.fark')}: ΔC ${isaret(dC)}${fmt(Math.abs(dC), 3)} · ΔT ${isaret(dT)}${fmt(Math.abs(dT), 0)} °C
      <br>${t('pin.kisayol')}</div>`;
  kart.hidden = false;
  // imlecin yanına, kutunun dışına taşmadan
  const kw = kart.offsetWidth, kh = kart.offsetHeight, cw = kutu.clientWidth, ch = kutu.clientHeight;
  let x = px + 16, y = py + 16;
  if (x + kw > cw - 4) x = px - kw - 16;
  if (y + kh > ch - 4) y = py - kh - 16;
  kart.style.left = Math.max(4, x) + 'px';
  kart.style.top = Math.max(4, y) + 'px';
}

/* ---------- araç düğmeleri ---------- */
// Tek sabit varsa "Sabiti sil" doğrudan siler; birden fazlaysa aşağı açılan listeden hangisi seçilir
let silMenuAcik = false;
const pinBul = (id) => st.pinler.find((p) => String(p.id) === id);

function pinAraclari() {
  let k = document.getElementById('pinAraclar');
  if (!k) {
    k = document.createElement('span');
    k.id = 'pinAraclar';
    k.className = 'pin-araclar';
    document.querySelector('.gorunum .pin-yuva').append(k);
    k.addEventListener('click', (e) => {
      const b = e.target.closest('[data-pin]');
      if (!b) return;
      const is = b.dataset.pin;
      if (is === 'ekle') pinEkle(st.C, st.T);
      else if (is === 'menu') { silMenuAcik = !silMenuAcik; pinAraclari(); }
      else if (is === 'tek') pinSil(gorunenPinler()[0]);
      else if (is === 'sil') {
        const p = pinBul(b.dataset.id);
        if (p) pinSil(p);
        if (gorunenPinler().length < 2) silMenuAcik = false;
        pinAraclari();
      } else if (is === 'hepsi') {
        const anahtar = kaynakAnahtari();
        st.pinler = st.pinler.filter((p) => p.kaynak !== anahtar);
        silMenuAcik = false;
        st.pinUstunde = null; kartGizle(); pinKaydet(); pinAraclari(); guncelle();
      }
    });
    // listede bir satırın üstüne gelince o nokta diyagramda vurgulansın
    k.addEventListener('mouseover', (e) => {
      const b = e.target.closest('[data-pin="sil"]');
      const p = b ? pinBul(b.dataset.id) : null;
      if (p !== st.pinUstunde) { st.pinUstunde = p; kartGizle(); guncelle(); }
    });
    k.addEventListener('mouseleave', () => { if (st.pinUstunde) { st.pinUstunde = null; guncelle(); } });
    // dışarı tıklayınca liste kapansın (composedPath: tıklanan düğme yeniden çizimle DOM'dan kalksa da doğru çalışır)
    document.addEventListener('click', (e) => {
      if (silMenuAcik && !e.composedPath().includes(k)) { silMenuAcik = false; pinAraclari(); }
    });
  }
  const liste = gorunenPinler(), n = liste.length;
  if (n < 2) silMenuAcik = false;
  let sil = '';
  if (n === 1) sil = `<button data-pin="tek" title="${t('pin.tekSil.ipucu')}">${t('pin.tekSil')}</button>`;
  else if (n > 1) {
    sil = `<span class="sil-menu">
      <button data-pin="menu" aria-expanded="${silMenuAcik}" title="${t('pin.menu.ipucu')}">${t('pin.menu', { n })} <span class="ok">${silMenuAcik ? '▴' : '▾'}</span></button>
      ${silMenuAcik ? `<span class="sil-liste" role="menu">
        ${liste.map((p, i) => `<button data-pin="sil" data-id="${p.id}" role="menuitem">
          <span class="pk-no">${i + 1}</span><span>${fmtC(p.w)} C · ${fmtT(p.T)}</span><span class="carpi">×</span></button>`).join('')}
        <button data-pin="hepsi" class="hepsi" role="menuitem">${t('pin.hepsi')}</button>
      </span>` : ''}
    </span>`;
  }
  k.innerHTML = `<button data-pin="ekle" title="${t('pin.ekle.ipucu')}">＋ ${t('pin.ekle')}</button>` + sil;
}
document.getElementById('ipucu').textContent = t('ipucu');
pinAraclari();
// kaynak değişince (ikili ↔ kesit) düğmedeki sayı güncellensin
KANCA.panel.push(() => { const n = gorunenPinler().length; if (pinAraclari.son !== n + kaynakAnahtari()) { pinAraclari.son = n + kaynakAnahtari(); pinAraclari(); } });
