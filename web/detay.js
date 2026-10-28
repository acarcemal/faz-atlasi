'use strict';
/* Aşama 2 — "Detay" modu (empirik).
   - Alaşım etkisi: hesaplanan ikili Fe–C sınırlarının üstüne Andrews (1965) alaşım
     katsayıları eklenir. Alaşım sıfırken her şey CALPHAD değeriyle birebir aynıdır.
   - Ötektoid karbon kayması: Bain diyagramından okunmuş yaklaşık doğrusal eğimler
     (Andrews'in Ac1/Ac3 katsayıları Mo, V, Si için ters yön veriyor).
   - Ms: Andrews doğrusal formülü; kalıntı östenit: Koistinen–Marburger;
     martenzit sertliği: Hodge–Orehoski; sertleşebilirlik: ASTM A255 (Grossmann DI).
   app.js'teki globalleri (st, el, sx, sy, svg, M, W, H, INV, POLY, fmt, ...) kullanır. */

const ELEMENTLER = [
  // sembol, ad, Andrews geçerlilik üst sınırı (yaklaşık), ötektoid C eğimi (%C / %element)
  { s: 'Mn', ad: t('el.Mn'), max: 2.0, eut: -0.07, tip: 'γ' },
  { s: 'Si', ad: t('el.Si'), max: 1.5, eut: -0.09, tip: 'α' },
  { s: 'Cr', ad: t('el.Cr'), max: 5.0, eut: -0.09, tip: 'α' },
  { s: 'Ni', ad: t('el.Ni'), max: 5.0, eut: -0.06, tip: 'γ' },
  { s: 'Mo', ad: t('el.Mo'), max: 1.0, eut: -0.17, tip: 'α' },
  { s: 'V',  ad: t('el.V'),  max: 0.3, eut: -0.30, tip: 'α' },
  { s: 'W',  ad: t('el.W'),  max: 4.0, eut: -0.08, tip: 'α' },
  { s: 'Cu', ad: t('el.Cu'), max: 1.0, eut: -0.05, tip: 'γ' },
];

// hazır çelikler artık kütüphanede: veri/celikler.js (hesap/celik_kutuphanesi.py)

const BANTLAR = [
  { k: 'tavlama', ad: t('bant.tavlama'), renk: 'var(--bant-tavlama)', aciklama: t('bant.tavlama.a') },
  { k: 'normal',  ad: t('bant.normal'),  renk: 'var(--bant-normal)',  aciklama: t('bant.normal.a') },
  { k: 'kuresel', ad: t('bant.kuresel'), renk: 'var(--bant-kuresel)', aciklama: t('bant.kuresel.a') },
  { k: 'gerilim', ad: t('bant.gerilim'), renk: 'var(--bant-gerilim)', aciklama: t('bant.gerilim.a') },
];

const ORTAMLAR = {
  firin: t('ortam.firin'),
  hava:  t('ortam.hava'),
  yag:   t('ortam.yag'),
  su:    t('ortam.su'),
};

st.detay = false;
st.alas = Object.fromEntries(ELEMENTLER.map((e) => [e.s, 0]));
st.ortam = 'su';
st.bant = { tavlama: true, normal: true, kuresel: false, gerilim: false };

/* ---------- ikili (hesaplanan) eğriler ---------- */
function egri(noktalar) {
  // (C, T) noktalarından C'ye göre doğrusal ara değer
  const p = noktalar.slice().sort((a, b) => a[0] - b[0]);
  return (C) => {
    if (C <= p[0][0]) return p[0][1];
    if (C >= p[p.length - 1][0]) return p[p.length - 1][1];
    let lo = 0, hi = p.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (p[m][0] <= C) lo = m; else hi = m; }
    const [c0, t0] = p[lo], [c1, t1] = p[hi];
    return c1 === c0 ? t0 : t0 + (C - c0) / (c1 - c0) * (t1 - t0);
  };
}
const A3_HESAP = egri(POLY.find((P) => key(P.p) === 'A+G').sag);
const ACM_HESAP = egri(POLY.find((P) => key(P.p) === 'G+C').sol);
const A1_H = INV.otektoid.T, WE_H = INV.otektoid.G, T0_H = INV.Fe_alfa_gama.T, GMAX_H = INV.otektik.G;

/* ---------- alaşımlı model ---------- */
function model(a = st.alas) {
  const dA1 = -10.7 * a.Mn - 16.9 * a.Ni + 29.1 * a.Si + 16.9 * a.Cr + 6.38 * a.W;
  const dA3 = -30 * a.Mn - 11 * a.Cr - 15.2 * a.Ni + 44.7 * a.Si + 104 * a.V + 31.5 * a.Mo + 13.1 * a.W - 20 * a.Cu;
  const we = Math.max(0.25, WE_H + ELEMENTLER.reduce((t, e) => t + e.eut * a[e.s], 0));
  const A1 = A1_H + dA1;
  const T0 = Math.max(T0_H + dA3, A1 + 20);
  const gmax = GMAX_H * we / WE_H;
  const A3 = (C) => C >= we ? A1 : A1 + (A3_HESAP(C * WE_H / we) - A1_H) * (T0 - A1) / (T0_H - A1_H);
  const Acm = (C) => {
    if (C <= we) return A1;
    const s = Math.min(GMAX_H, WE_H + (C - we) * (GMAX_H - WE_H) / (gmax - we));
    return ACM_HESAP(s) + dA1;
  };
  const alasimli = ELEMENTLER.some((e) => a[e.s] > 0);
  return { dA1, dA3, we, A1, T0, gmax, A3, Acm, alasimli };
}

function msHesap(C, a = st.alas) {
  return 539 - 423 * C - 30.4 * a.Mn - 17.7 * a.Ni - 12.1 * a.Cr - 7.5 * a.Mo;
}
function martenzitHRC(C) {
  if (C > 0.6) return null;
  const x = C;
  return 35.395 + 6.990 * x + 312.330 * x ** 2 - 821.744 * x ** 3 + 1015.479 * x ** 4 - 538.346 * x ** 5;
}
/** ASTM A255 ideal kritik çap (mm), ASTM tane boyutu 7 */
function DIhesap(C, a = st.alas) {
  let b;
  const c = Math.min(C, 0.9);
  if (c <= 0.39) b = 0.54 * c;
  else if (c <= 0.55) b = 0.171 + 0.001 * c + 0.265 * c * c;
  else if (c <= 0.65) b = 0.115 + 0.268 * c - 0.038 * c * c;
  else if (c <= 0.75) b = 0.143 + 0.2 * c;
  else b = 0.062 + 0.409 * c - 0.135 * c * c;
  const fMn = a.Mn <= 1.2 ? 1 + 3.3333 * a.Mn : 5.1 * a.Mn - 1.12;
  const f = fMn * (1 + 0.7 * a.Si) * (1 + 0.363 * a.Ni) * (1 + 2.16 * a.Cr) * (1 + 3.0 * a.Mo) * (1 + 1.73 * a.V) * (1 + 0.365 * a.Cu);
  return b * f * 25.4;
}

/** Kritik sıcaklıklar: kesit açıksa gerçek hesap (kesit.js), değilse empirik model.
    ae3: ferritin bittiği sıcaklık (hiperötektoidde A1 bandının üstü), aecm: son karbürün çözündüğü sıcaklık,
    tam: tam östenit sıcaklığı (hipoda ferrit ve alaşım karbürlerinin ikisi de bitmiş; hiperde Acm) */
function kritik(C, m = model()) {
  if (KAYNAK.alt) return KAYNAK.alt.kritik(C);
  const hipo = C < m.we;
  return { ae1: m.A1, ae3: hipo ? m.A3(C) : m.A1, aecm: hipo ? null : m.Acm(C), hipo, tam: hipo ? m.A3(C) : m.Acm(C), kaynak: 'empirik' };
}

/** Bir karbon değeri için ısıl işlem sıcaklık aralıkları (hesaplanamayan için null).
    Sertleştirme/tavlama: ferritin bittiği çizginin (A3 / A1 bandı üstü) +30–50 °C üstü.
    Normalizasyon: tam östenit çizgisinin (ferrit ve karbürlerin ikisinin de bittiği yer; ikilide hipoda A3, hiperde Acm)
    +50–70 °C üstü. İki çizgi de karbon boyunca kesintisiz olduğu için bantlar ötektoid civarında kırılmaz. */
function islemAraliklari(C, m = model()) {
  const k = kritik(C, m);
  const ekle = (T, a, b) => (T == null ? null : [T + a, T + b]);
  return {
    tavlama: ekle(k.ae3, 30, 50),
    normal: ekle(k.tam, 50, 70),
    kuresel: ekle(k.ae1, -30, 0),
    gerilim: [550, 650],
  };
}

/* ---------- çizim ---------- */
KANCA.ciz.push(() => {
  if (!st.detay) return;
  const m = model();
  const g = el('g', { 'clip-path': 'url(#kirp)' }, svg);
  const cMax = KAYNAK.alt ? KAYNAK.alt.sinir.x[1] : Math.min(m.gmax, 1.8);
  const N = KAYNAK.alt ? 120 : 160;
  const Cs = Array.from({ length: N + 1 }, (_, i) => cMax * i / N);
  // tam kesişme noktası (ötektoid) bant köşesinde kaybolmasın
  if (!KAYNAK.alt) { Cs.push(m.we - 1e-6, m.we + 1e-6); Cs.sort((a, b) => a - b); }

  // bant adları diyagramda değil lejantta (bantLejant); lejantta üstüne gelinen bant vurgulanır
  for (const b of st.katman.bant ? BANTLAR : []) {
    if (!st.bant[b.k]) continue;
    const vurgu = st.bantVurgu ? (st.bantVurgu === b.k ? ' vurgu' : ' soluk') : '';
    // hesaplanamayan noktalarda bandı böl
    const parcalar = [[]];
    for (const C of Cs) {
      const ar = islemAraliklari(C, m)[b.k];
      if (ar) parcalar[parcalar.length - 1].push([C, ar]);
      else if (parcalar[parcalar.length - 1].length) parcalar.push([]);
    }
    for (const parca of parcalar) {
      if (parca.length < 2) continue;
      const alt = parca.map(([C, [t0]]) => sx(C).toFixed(1) + ',' + sy(t0).toFixed(1));
      const ust = parca.map(([C, [, t1]]) => sx(C).toFixed(1) + ',' + sy(t1).toFixed(1));
      el('polygon', { points: [...alt, ...ust.reverse()].join(' '), class: 'bant' + vurgu, style: `fill:${b.renk};stroke:${b.renk}` }, g);
    }
  }

  // empirik (Andrews) çizgiler: noktalı, ucunda kısa adı
  if (m.alasimli && st.katman.emp) {
    const yol = (f, c0, c1) => {
      const p = [];
      for (let i = 0; i <= 120; i++) { const C = c0 + (c1 - c0) * i / 120; p.push((i ? 'L' : 'M') + sx(C).toFixed(1) + ',' + sy(f(C)).toFixed(1)); }
      return p.join('');
    };
    const yazi = (x, y, t, anchor = 'start') => { el('text', { x, y, class: 'alas-yazi', 'text-anchor': anchor }, g).textContent = t; };
    el('path', { d: yol(m.A3, 0, m.we), class: 'alas-cizgi' }, g);
    el('path', { d: yol(m.Acm, m.we, m.gmax), class: 'alas-cizgi' }, g);
    el('path', { d: `M${sx(0.02)},${sy(m.A1)}L${sx(W_CEM)},${sy(m.A1)}`, class: 'alas-cizgi' }, g);
    el('circle', { cx: sx(m.we), cy: sy(m.A1), r: 3, class: 'alas-nokta' }, g);
    // adlar: A3' üst ucunda, Acm' görünen sağ ucunda, A1' sağ kenarda
    yazi(sx(0) + 6, sy(m.T0) - 5, "A3′");
    const cAcm = Math.min(m.gmax, st.view.x[1]) - 0.02 * (st.view.x[1] - st.view.x[0]);
    if (cAcm > m.we) yazi(sx(cAcm), sy(m.Acm(cAcm)) - 6, "Acm′", 'end');
    yazi(W - M.r - 6, sy(m.A1) - 5, `A1′ ${fmt(m.A1, 0)} °C`, 'end');
  }
});

/* ---------- panel ---------- */
const $ = (id) => document.getElementById(id);

/* ---------- çelik kütüphanesi ve kayıtlı çelikler ---------- */
const KUTUPHANE = window.CELIK_KUTUPHANE || [];
const KAYIT_ANAHTAR = 'fec-celiklerim-v1';
let kayitliCelikler = (() => {
  // bozuk ya da eski biçimli kayıtları ele: { ad: metin, C: sayı, alas: { element: sayı } }
  try {
    const l = JSON.parse(localStorage.getItem(KAYIT_ANAHTAR));
    return Array.isArray(l) ? l.filter((c) => c && typeof c.ad === 'string' && isFinite(c.C) && c.alas && typeof c.alas === 'object') : [];
  } catch (e) { return []; }
})();
function kayitliKaydet() {
  try { localStorage.setItem(KAYIT_ANAHTAR, JSON.stringify(kayitliCelikler)); } catch (e) { /* gizli pencere */ }
}
st.celik = null;   // { tur: 'kutuphane' | 'kayitli', ad, C }
// kütüphanedeki grup ve kullanım alanı seçili dilde
const grupAd = (c) => (DIL === 'en' ? c.grup_en : c.grup);
const kullanimAd = (c) => (DIL === 'en' ? c.kullanim_en : c.kullanim);

/** Kesit anahtarı: hesap/celik_kutuphanesi.py alas_anahtari() ile aynı biçim */
function alasAnahtari(a = st.alas) {
  return ELEMENTLER.filter((e) => a[e.s] > 0).map((e) => e.s + String(+a[e.s].toFixed(3))).join('_') || 'saf';
}
// arama: büyük/küçük harf, boşluk, nokta, tire ve Türkçe karakter farkı gözetmeden
const sade = (t) => String(t).toLocaleLowerCase('tr').replace(/[\s.\-_/()≈]/g, '')
  .replace(/ı/g, 'i').replace(/ş/g, 's').replace(/ğ/g, 'g').replace(/ü/g, 'u').replace(/ö/g, 'o').replace(/ç/g, 'c');

function alasKartiKur() {
  $('kAlas').innerHTML = `
    ${baslik(t('kart.alas'), t('kart.alas.meta'))}
    <div class="celik-ara">
      <input id="celikAra" type="search" autocomplete="off" spellcheck="false"
        placeholder="${t('ara.ph')}" aria-label="${t('ara.aria')}">
      <div id="celikListe" class="celik-liste" role="listbox" hidden></div>
    </div>
    <div id="celikBilgi" class="celik-bilgi" hidden></div>
    <label class="gercek-sec" id="gercekKutu"><input type="checkbox" id="gercekSec" checked>
      <span><b>${t('gercek.baslik')}</b><br><span class="soluk" id="gercekNot"></span></span></label>
    <div class="alas-grid">${ELEMENTLER.map((e) => `
      <label title="${e.ad} · ${t(e.tip === 'γ' ? 'gamajen.ipucu' : 'alfajen.ipucu')}">
        <span>${e.s}<small class="${e.tip === 'γ' ? 'gama' : 'alfa'}">${e.tip}</small></span>
        <input type="text" inputmode="decimal" autocomplete="off" spellcheck="false" data-adim="0.05" value="0" data-el="${e.s}">
      </label>`).join('')}
    </div>
    <div class="kucuk soluk" style="margin-top:6px"><small class="gama">γ</small> ${t('gamajen.aciklama')} · <small class="alfa">α</small> ${t('alfajen.aciklama')}</div>
    <div class="kaydet-satir">
      <input id="kayitAd" type="text" maxlength="40" placeholder="${t('kayit.ph')}">
      <button id="kaydetBtn" class="kucuk-buton">${t('kaydet')}</button>
      <button id="alasSifir" class="kucuk-buton">${t('sifirla')}</button>
    </div>
    <div id="kayitNot" class="kucuk soluk" hidden></div>`;

  $('kAlas').querySelectorAll('input[data-el]').forEach((i) => i.addEventListener('input', () => {
    const v = sayiOku(i.value);
    st.alas[i.dataset.el] = isFinite(v) && v > 0 ? v : 0;
    // bileşim seçilen çelikten saptı: artık o çelik değil
    celikBirak();
    kesitGuncelle();
    guncelle();
  }));
  $('gercekSec').addEventListener('change', () => { kesitGuncelle(); guncelle(); });
  $('alasSifir').addEventListener('click', () => {
    for (const e of ELEMENTLER) st.alas[e.s] = 0;
    celikBirak();
    alasGirisleriniYaz();
    kesitGuncelle();
    guncelle();
  });
  $('kaydetBtn').addEventListener('click', celikKaydet);
  $('kayitAd').addEventListener('keydown', (e) => { if (e.key === 'Enter') celikKaydet(); });

  // arama listesi
  const ara = $('celikAra'), liste = $('celikListe');
  ara.addEventListener('focus', () => listeAc());
  ara.addEventListener('input', () => listeAc());
  ara.addEventListener('keydown', (e) => {
    const ogeler = [...liste.querySelectorAll('[data-secim]')];
    let i = ogeler.findIndex((o) => o.classList.contains('odak'));
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (liste.hidden) listeAc();
      i = e.key === 'ArrowDown' ? Math.min(i + 1, ogeler.length - 1) : Math.max(i - 1, 0);
      ogeler.forEach((o, j) => o.classList.toggle('odak', j === i));
      if (ogeler[i]) ogeler[i].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const o = ogeler[Math.max(i, 0)];
      if (o) secimUygula(o.dataset.secim);
    } else if (e.key === 'Escape') {
      listeKapat(); ara.blur();
    }
  });
  liste.addEventListener('mousedown', (e) => e.preventDefault());   // tıklarken arama kutusu odağı kaybetmesin
  liste.addEventListener('click', (e) => {
    const sil = e.target.closest('[data-kayit-sil]');
    if (sil) { kayitliSil(sil.dataset.kayitSil); return; }
    const o = e.target.closest('[data-secim]');
    if (o) secimUygula(o.dataset.secim);
  });
  ara.addEventListener('blur', () => setTimeout(listeKapat, 120));

  $('kIslem').addEventListener('change', (e) => {
    if (e.target.dataset.bant) { st.bant[e.target.dataset.bant] = e.target.checked; guncelle(); }
  });
  $('kSogu').addEventListener('change', (e) => {
    if (e.target.name === 'ortam') { st.ortam = e.target.value; guncelle(); }
  });
  celikBilgiYaz();
  kesitGuncelle();
}

function listeAc() {
  const q = sade($('celikAra').value);
  const eslesir = (...alanlar) => !q || alanlar.some((a) => a && sade(a).includes(q));
  const kayitli = kayitliCelikler.filter((c) => eslesir(c.ad));
  // iki dilde de aranır: İngilizce arayüzde "yay" da "spring" de bulur
  const kut = KUTUPHANE.filter((c) => eslesir(c.ad, c.no, c.aisi, c.grup, c.kullanim, c.grup_en, c.kullanim_en));
  const hesap = (anahtar) => (kesitVar(anahtar) ? `<span class="hesap-var" title="${t('hesap.var.ipucu')}">● ${t('hesap.var')}</span>` : '');
  const kayitliHtml = kayitli.map((c) => `
    <div class="celik-oge kayitli" data-secim="k:${encodeURIComponent(c.ad)}" role="option">
      <div><b>${esc(c.ad)}</b> <span class="etiket-kayitli">${t('kayitli')}</span>${hesap(alasAnahtari(c.alas))}</div>
      <div class="alt">C ${yuzde(fmt(c.C, 2))}${ELEMENTLER.filter((e) => c.alas[e.s] > 0).map((e) => ` · ${e.s} ${yuzde(fmt(c.alas[e.s], 2))}`).join('')}</div>
      <button class="oge-sil" data-kayit-sil="${encodeURIComponent(c.ad)}" title="${t('kayit.sil')}">×</button>
    </div>`).join('');
  const kutHtml = kut.map((c) => `
    <div class="celik-oge" data-secim="l:${encodeURIComponent(c.ad)}" role="option">
      <div><b>${c.ad}</b> <span class="soluk">${c.no !== '—' ? c.no : ''}${c.aisi !== '—' ? ' · AISI ' + c.aisi : ''}</span>${hesap(c.anahtar)}</div>
      <div class="alt">${grupAd(c)} · ${kullanimAd(c)}</div>
    </div>`).join('');
  $('celikListe').innerHTML = (kayitliHtml + kutHtml) || `<div class="celik-bos">${t('ara.bos')}</div>`;
  $('celikListe').hidden = false;
}
function listeKapat() { $('celikListe').hidden = true; }

function secimUygula(secim) {
  const [tur, adK] = [secim.slice(0, 1), decodeURIComponent(secim.slice(2))];
  let C, alas;
  if (tur === 'k') {
    const c = kayitliCelikler.find((x) => x.ad === adK);
    if (!c) return;
    C = c.C; alas = c.alas;
    st.celik = { tur: 'kayitli', ad: c.ad, C };
  } else {
    const c = KUTUPHANE.find((x) => x.ad === adK);
    if (!c) return;
    C = c.nominal.C; alas = c.nominal;
    st.celik = { tur: 'kutuphane', ad: c.ad, C };
  }
  for (const e of ELEMENTLER) st.alas[e.s] = alas[e.s] || 0;
  alasGirisleriniYaz();
  $('celikAra').value = st.celik.ad;
  listeKapat();
  $('celikAra').blur();
  celikBilgiYaz();
  kesitGuncelle();
  sec(C, null);
}
function celikBirak() {
  if (!st.celik) return;
  st.celik = null;
  $('celikAra').value = '';
  celikBilgiYaz();
}

/** Seçilen çeliğin künyesi ve standart aralıkları */
function celikBilgiYaz() {
  const k = $('celikBilgi');
  if (!st.celik) { k.hidden = true; return; }
  k.hidden = false;
  if (st.celik.tur === 'kayitli') {
    k.innerHTML = `<span class="etiket-kayitli">${t('kayitli')}</span> <b>${esc(st.celik.ad)}</b> · ${t('kayitli.aciklama')}`;
    return;
  }
  const c = KUTUPHANE.find((x) => x.ad === st.celik.ad);
  const aralik = Object.entries(c.aralik).map(([e, [a, b]]) =>
    `${e} ${a > 0 ? fmt(a, 2) + '–' : '≤ '}${fmt(b, 2)}`).join(' · ');
  k.innerHTML = `<b>${c.ad}</b>${c.no !== '—' ? ' · ' + c.no : ''}${c.aisi !== '—' ? ' · AISI/SAE ' + c.aisi : ''} · ${grupAd(c)}
    <div class="soluk">${c.std} · ${kullanimAd(c)}</div>
    <div class="soluk">${t('celik.aralik', { aralik })}</div>`;
}

function celikKaydet() {
  const ad = $('kayitAd').value.trim();
  const not = $('kayitNot');
  not.hidden = false;
  if (!ad) { not.textContent = t('kayit.adYok'); return; }
  const alas = Object.fromEntries(ELEMENTLER.filter((e) => st.alas[e.s] > 0).map((e) => [e.s, st.alas[e.s]]));
  const kayit = { ad, C: +st.C.toFixed(3), alas, tarih: new Date().toISOString().slice(0, 10) };
  const var_ = kayitliCelikler.findIndex((c) => c.ad === ad);
  if (var_ >= 0) kayitliCelikler[var_] = kayit; else kayitliCelikler.unshift(kayit);
  kayitliKaydet();
  st.celik = { tur: 'kayitli', ad, C: kayit.C };
  $('celikAra').value = ad;
  $('kayitAd').value = '';
  not.textContent = t(var_ >= 0 ? 'kayit.guncellendi' : 'kayit.kaydedildi', { ad, C: yuzde(fmt(kayit.C, 2)) });
  celikBilgiYaz();
  kesitGuncelle();
}
function kayitliSil(adK) {
  const ad = decodeURIComponent(adK);
  kayitliCelikler = kayitliCelikler.filter((c) => c.ad !== ad);
  kayitliKaydet();
  if (st.celik && st.celik.tur === 'kayitli' && st.celik.ad === ad) celikBirak();
  listeAc();
}

/** Detay açık + bu alaşımın kesiti hesaplanmış + kutu işaretli ise gerçek hesaba geç */
function kesitGuncelle() {
  const anahtar = alasAnahtari();
  const hazir = kesitVar(anahtar);
  const ad = st.celik ? st.celik.ad : t('girilen.bilesim');
  if (st.detay && hazir && $('gercekSec').checked) kesitAc(anahtar, { ad, C: st.celik ? st.celik.C : null });
  else kesitKapat();
  const alasimli = ELEMENTLER.some((e) => st.alas[e.s] > 0);
  $('gercekNot').textContent = hazir
    ? t('gercek.var', { ad: st.celik ? st.celik.ad : t('bu.bilesim') })
    : st.celik && st.celik.tur === 'kutuphane'
      ? t('gercek.sirada', { ad: st.celik.ad })
      : alasimli ? t('gercek.yok') : t('gercek.ipucu');
}
function alasGirisleriniYaz() {
  $('kAlas').querySelectorAll('input[data-el]').forEach((i) => { i.value = sayiYaz(st.alas[i.dataset.el]); });
}

/* ---------- katman düğmeleri ve bant lejantı ---------- */
const KATMANLAR = [
  { k: 'faz', ad: t('katman.faz') },
  { k: 'bant', ad: t('katman.bant') },
  { k: 'emp', ad: t('katman.emp') },
  { k: 'etiket', ad: t('katman.etiket') },
];
function katmanKur() {
  $('katmanlar').innerHTML = `<span>${t('katmanlar')}:</span>` +
    KATMANLAR.map((k) => `<button data-katman="${k.k}" aria-pressed="false">${k.ad}</button>`).join('') +
    `<span class="katman-not" id="empNot" hidden>${t('katman.empNot')}</span>`;
  $('katmanlar').addEventListener('click', (e) => {
    const k = e.target.dataset && e.target.dataset.katman;
    if (!k) return;
    st.katman[k] = !st.katman[k];
    guncelle();
  });
  // lejantta bandın üstüne gelince o bant vurgulanır; diğerleri soluklaşır
  $('bantLejant').addEventListener('mouseover', (e) => {
    const k = e.target.closest('[data-bant-lejant]');
    const yeni = k ? k.dataset.bantLejant : null;
    if (yeni !== st.bantVurgu) { st.bantVurgu = yeni; guncelle(); }
  });
  $('bantLejant').addEventListener('mouseleave', () => { if (st.bantVurgu) { st.bantVurgu = null; guncelle(); } });
}
let sonBantLejant = '';
function katmanGuncelle() {
  document.body.classList.toggle('detay-acik', st.detay);
  document.body.classList.toggle('kesit-acik', !!KAYNAK.alt);
  $('katmanlar').hidden = !st.detay;
  $('bantLejant').hidden = !st.detay || !st.katman.bant;
  const alasimli = model().alasimli;
  $('katmanlar').querySelectorAll('button').forEach((b) => {
    // empirik çizgiler sadece alaşım girilmişse anlamlı
    const pasif = b.dataset.katman === 'emp' && !alasimli;
    b.disabled = pasif;
    b.classList.toggle('aktif', !pasif && !!st.katman[b.dataset.katman]);
    b.setAttribute('aria-pressed', !pasif && !!st.katman[b.dataset.katman]);
  });
  $('empNot').hidden = alasimli;
  if (!st.detay) return;
  const r = islemAraliklari(st.C);
  const html = `<span>${t('bantlar.lejant', { C: fmtC(st.C) })}:</span>` + BANTLAR.filter((b) => st.bant[b.k]).map((b) =>
    `<span class="bant-chip" data-bant-lejant="${b.k}"><i style="background:${b.renk}"></i>${b.ad} <b>${r[b.k] ? fmt(r[b.k][0], 0) + '–' + fmt(r[b.k][1], 0) + ' °C' : '—'}</b></span>`).join('');
  if (html !== sonBantLejant) { $('bantLejant').innerHTML = html; sonBantLejant = html; }
}

KANCA.panel.push(() => {
  const acik = st.detay;
  for (const id of ['kAlas', 'kIslem', 'kSogu']) $(id).hidden = !acik;
  katmanGuncelle();
  if (!acik) return;
  const w = st.C, m = model(), a = st.alas;
  const k = kritik(w, m), gercek = k.kaynak === 'hesap';
  const hipo = k.hipo;

  // geçerlilik uyarıları
  const uyarilar = [];
  if (!gercek) {
    if (w > 0.6) uyarilar.push(t('uyari.andrewsC', { C: fmtC(w), sinir: fmtC(0.6) }));
    for (const e of ELEMENTLER) if (a[e.s] > e.max) uyarilar.push(t('uyari.element', { e: e.s, deger: yuzde(fmt(a[e.s], 2)), sinir: yuzde(fmt(e.max, 1)) }));
    if (w > m.gmax) uyarilar.push(t('uyari.dokme'));
  } else if (w > 0.6) {
    uyarilar.push(t('uyari.msEmpirik', { sinir: fmtC(0.6) }));
  }
  const uyari = uyarilar.length ? `<div class="uyari">${uyarilar.join('<br>')}</div>` : '';

  // ısıl işlem kartı
  const r = islemAraliklari(w, m);
  const sinifAd = t(hipo ? 'hipo.k' : 'hiper.k');
  const kare = (ad, deger, alt) => `<div class="kare"><b>${ad}</b><span>${deger}</span>${alt ? `<div class="kucuk soluk">${alt}</div>` : ''}</div>`;
  const aralik = (t) => (t ? `${fmt(t[0], 0)}–${fmt(t[1], 0)} °C` : '—');
  const T0 = (T) => (T == null ? '—' : fmt(T, 0) + ' °C');
  const satir = (b) => `<tr><td><label class="bant-sec"><input type="checkbox" data-bant="${b.k}" ${st.bant[b.k] ? 'checked' : ''}>
      <i style="background:${b.renk}"></i><b>${b.ad}</b></label><span class="soluk">${b.aciklama}</span></td>
      <td class="sag"><b>${aralik(r[b.k])}</b></td></tr>`;
  $('kIslem').innerHTML = `
    ${baslik(t('kart.islem'), `${fmtC(w)} C · ${t(gercek ? 'kaynak.hesap' : m.alasimli ? 'kaynak.empirik' : 'kaynak.ikili')}`)}
    ${gercek ? `<div class="kritik-ust">
      ${kare('Ae1', k.ae1Alt ? '< 550 °C' : T0(k.ae1), t('gk.Ae1.k'))}
      ${kare(hipo ? 'Ae3' : t('kare.A1ustu'), T0(k.ae3), t('gk.Ae3.k'))}
      ${hipo && k.aecm != null && k.aecm > (k.ae3 ?? 0) + 1
        ? kare(t('kare.karburCoz'), T0(k.aecm), t('kare.alasimKarburu'))
        : kare(hipo ? t('kare.sinif') : 'Aecm', hipo ? t('kare.hipo') : T0(k.aecm), hipo ? t('hipo.k') : t('gk.Aecm.k'))}
    </div>
    ${k.ae1Alt ? `<div class="kucuk soluk">${t('not.yuksekNi')}</div>` : ''}
    ${hipo && k.aecm != null && k.aecm > (k.ae3 ?? 0) + 1 ? `<div class="kucuk soluk">${t('not.karburCozunme', { T: fmt(k.aecm, 0), T30: fmt(k.aecm + 30, 0) })}</div>` : ''}
    <div class="kucuk soluk">${t('not.empirikKarsilastirma', { A1: fmt(m.A1, 0), ikinci: m.we > w ? `A3′ ${fmt(m.A3(w), 0)}` : `Acm′ ${fmt(m.Acm(w), 0)}` })}</div>`
    : `<div class="kritik-ust">
      ${kare('A1' + (m.alasimli ? '′' : ''), fmt(m.A1, 0) + ' °C')}
      ${kare(hipo ? 'A3' + (m.alasimli ? '′' : '') : 'Acm' + (m.alasimli ? '′' : ''), fmt(hipo ? m.A3(w) : m.Acm(w), 0) + ' °C')}
      ${kare(t('kare.otektoidC'), fmtC(m.we), sinifAd)}
    </div>`}
    <table class="liste">${BANTLAR.map(satir).join('')}</table>
    ${hipo ? '' : `<div class="kucuk" style="margin-top:8px">${t('not.hiperSertlestirme')}</div>`}
    ${m.alasimli && !gercek ? `<div class="kucuk" style="margin-top:8px">${t('not.ureticiEmpirik')}</div>` : ''}
    ${gercek ? `<div class="kucuk" style="margin-top:8px">${t('not.ureticiHesap')}</div>` : ''}
    ${m.alasimli && !gercek ? `<div class="kucuk soluk" style="margin-top:6px">${t('not.alasimKaymasi', { dA1: fmt(m.dA1, 0), dA3: fmt(m.dA3, 0), we0: fmtC(WE_H), we: fmtC(m.we) })}</div>` : ''}
    ${uyari}`;

  // soğuma kartı
  const Ms = msHesap(w), Mf = Ms - 215;
  const fM = Ms > 20 ? 1 - Math.exp(-0.011 * (Ms - 20)) : 0;
  const hrc = martenzitHRC(w);
  const DI = DIhesap(w);
  const sertlesebilirlik = t(DI < 25 ? 'sb.dusuk' : DI < 60 ? 'sb.orta' : DI < 120 ? 'sb.yuksek' : 'sb.cokYuksek');
  const yapi = sogumaYapisi(w, m, DI, fM, k);
  $('kSogu').innerHTML = `
    ${baslik(t('kart.sogu'), ORTAMLAR[st.ortam])}
    <div class="ortamlar">${Object.entries(ORTAMLAR).map(([k, ad]) => `<label class="${st.ortam === k ? 'secili' : ''}"><input type="radio" name="ortam" value="${k}" ${st.ortam === k ? 'checked' : ''}>${ad}</label>`).join('')}</div>
    <div class="buyuk" style="margin-top:10px">${yapi.baslik}</div>
    <div class="kucuk" style="margin-top:4px">${yapi.aciklama}</div>
    <table class="liste" style="margin-top:10px">
      <tr><td>${t('sogu.Ms')}</td><td class="sag"><b>${fmt(Ms, 0)} °C</b></td></tr>
      <tr><td>${t('sogu.Mf')}</td><td class="sag">${fmt(Mf, 0)} °C</td></tr>
      <tr><td>${t('sogu.martenzit')}</td><td class="sag">${fmtP(fM)}</td></tr>
      <tr><td>${t('sogu.kalinti')}</td><td class="sag">${fmtP(1 - fM)}</td></tr>
      <tr><td>${t('sogu.hrc')}</td><td class="sag">${hrc ? '≈ ' + fmt(hrc, 0) + ' HRC' : '≈ 64–66 HRC'}</td></tr>
      <tr><td>${t('sogu.DI')}</td><td class="sag">${fmt(DI, 0)} mm · ${sertlesebilirlik}</td></tr>
    </table>
    <div class="kucuk soluk" style="margin-top:6px">${t('sogu.not', { cizgi: hipo ? 'A3' : 'A1' })}</div>`;
});

function sogumaYapisi(w, m, DI, fM, k) {
  const hipo = k.hipo;
  const etkt = k.kaynak === 'hesap' ? (k.aecm != null && k.ae3 != null && Math.abs(k.aecm - k.ae3) < 3) : Math.abs(w - m.we) < 0.02;
  // yapı adı: önce proötektoid faz (varsa), sonra perlit; dile göre ayrı kalıplar
  const pro = etkt ? 'yok' : hipo ? 'ferrit' : 'sementit';
  const kalinti = fM < 0.9 ? ' ' + t('sy.kalinti', { oran: fmtP(1 - fM) }) : '';
  const catlak = ' ' + t((w > 0.5 || DI > 60) ? 'sy.catlak' : 'sy.temper');
  const martenzit = t('sy.martenzit') + (fM < 0.95 ? ' ' + t('sy.artiKalinti') : '');
  switch (st.ortam) {
    case 'firin':
      return { baslik: t('sy.kabaPerlit.' + pro), aciklama: t('sy.firin.a') };
    case 'hava':
      if (DI > 150) return { baslik: t('sy.havaSertlesen'), aciklama: t('sy.havaSertlesen.a') + kalinti };
      return { baslik: t('sy.incePerlit.' + pro), aciklama: t('sy.hava.a') };
    case 'yag':
      if (DI >= 50) return { baslik: martenzit, aciklama: t('sy.yagYeterli') + kalinti + catlak };
      if (DI >= 25) return { baslik: t('sy.martenzitBeynit'), aciklama: t('sy.yagKismi.a') + catlak };
      return { baslik: t('sy.yagYetersiz'), aciklama: t('sy.yagYetersiz.a') };
    case 'su':
      if (w < 0.2) return { baslik: t('sy.dusukC'), aciklama: t('sy.dusukC.a') };
      if (DI >= 15) return { baslik: martenzit, aciklama: t('sy.suHizli') + kalinti + catlak };
      return { baslik: t('sy.suYetersiz'), aciklama: t('sy.suYetersiz.a') + catlak };
  }
}

/* ---------- Çalışma modu: "Faz diyagramı" | "Isıl işlem & alaşım" ---------- */
function detayAyarla(acik) {
  if (st.detay === acik) return;
  st.detay = acik;
  // katman düğmeleri sadece bu modda görünür; çıkınca temel görünümü geri getir
  if (!st.detay) Object.assign(st.katman, { faz: true, etiket: true });
  for (const [id, a] of [['modFaz', !acik], ['detayBtn', acik]]) {
    $(id).classList.toggle('aktif', a);
    $(id).setAttribute('aria-pressed', a);
  }
  kesitGuncelle();
  guncelle();
}
$('detayBtn').addEventListener('click', () => detayAyarla(true));
$('modFaz').addEventListener('click', () => detayAyarla(false));
alasKartiKur();
katmanKur();

/* ---------- dil değişince durum korunur (dil.js) ---------- */
function dilDurumuTopla() {
  return {
    C: st.C, T: st.T, detay: st.detay, alas: st.alas, celik: st.celik, ortam: st.ortam,
    bant: st.bant, katman: st.katman, gercek: $('gercekSec').checked,
  };
}
(() => {
  const d = dilDurumuAl();
  if (!d) return;
  if (isFinite(d.C)) st.C = d.C;
  if (isFinite(d.T)) st.T = d.T;
  if (d.alas) for (const e of ELEMENTLER) st.alas[e.s] = +d.alas[e.s] || 0;
  if (ORTAMLAR[d.ortam]) st.ortam = d.ortam;
  if (d.bant) Object.assign(st.bant, d.bant);
  if (d.katman) Object.assign(st.katman, d.katman);
  if (d.gercek === false) $('gercekSec').checked = false;
  alasGirisleriniYaz();
  if (d.celik && d.celik.ad) { st.celik = d.celik; $('celikAra').value = d.celik.ad; celikBilgiYaz(); }
  if (d.detay) detayAyarla(true); else kesitGuncelle();
})();
