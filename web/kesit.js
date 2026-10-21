'use strict';
/* Alaşımlı çelik kesitleri (izoplet): hesap/kesit_uret.py -> veri/kesitler.js
   MatCalc açık çelik veritabanı + pycalphad. Alaşım elementleri sabit, karbon değişken.
   Kesitte bağlantı çizgileri düzlemde olmadığı için kaldıraç kuralı uygulanmaz;
   faz oranları (ağırlıkça) ve fazların kendi karbonu doğrudan hesaptan, ızgaradan ara değerle gelir.
   app.js'teki KAYNAK arayüzünü doldurur. */

/* Kesitler seçilince yüklenir: veri/kesit/<anahtar>.js -> KESIT_YUKLE(anahtar, veri).
   Hesaplanmış anahtarların listesi veri/kesit/liste.js (KESIT_LISTE). Anahtar sadece alaşım
   elementlerinden oluşur (karbon kesit ekseni), biçimi hesap/celik_kutuphanesi.py ile aynıdır. */
const KESITLER = {};
const kesitBekleyen = {};
window.KESIT_YUKLE = (anahtar, veri) => {
  KESITLER[anahtar] = veri;
  if (kesitBekleyen[anahtar]) { kesitBekleyen[anahtar].forEach((f) => f()); delete kesitBekleyen[anahtar]; }
};
const kesitVar = (anahtar) => (window.KESIT_LISTE || []).includes(anahtar);
function kesitYukle(anahtar) {
  if (KESITLER[anahtar]) return Promise.resolve(KESITLER[anahtar]);
  return new Promise((ok, hata) => {
    const ilk = !kesitBekleyen[anahtar];
    (kesitBekleyen[anahtar] = kesitBekleyen[anahtar] || []).push(() => ok(KESITLER[anahtar]));
    if (!ilk) return;
    const sc = document.createElement('script');
    sc.src = `veri/kesit/${encodeURIComponent(anahtar)}.js`;
    sc.onerror = () => { delete kesitBekleyen[anahtar]; hata(new Error('kesit yüklenemedi: ' + anahtar)); };
    document.head.appendChild(sc);
  });
}

Object.assign(FAZ, {
  K7:  { ad: t('faz.K7'), kisa: 'M₇C₃' },
  K23: { ad: t('faz.K23'), kisa: 'M₂₃C₆' },
  K6:  { ad: t('faz.K6'), kisa: 'M₆C' },
  MC:  { ad: t('faz.MC'), kisa: 'MC' },
  M2C: { ad: t('faz.M2C'), kisa: 'M₂C' },
});
const KARBURLER = ['C', 'K7', 'K23', 'K6', 'MC', 'M2C'];
const ELEMENT_AD = { Mn: 'Mn', Si: 'Si', Cr: 'Cr', Ni: 'Ni', Mo: 'Mo', V: 'V', W: 'W', Cu: 'Cu' };

/** anahtar: kesit (alaşım) anahtarı · etiket: { ad: gösterilen çelik adı, C: çeliğin nominal karbonu } */
function kesitKaynak(anahtar, etiket) {
  const K = KESITLER[anahtar], ad = etiket.ad;
  const rows = K.rows, CG = K.C;
  const poly = poligonlar(rows);
  const sinir = { x: [0, CG[CG.length - 1]], y: [rows[0].T, rows[rows.length - 1].T] };

  const indeks = (T) => {
    let lo = 0, hi = rows.length - 1;
    if (T <= rows[0].T) return 0;
    if (T >= rows[hi].T) return hi - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (rows[m].T <= T) lo = m; else hi = m; }
    return lo;
  };
  function bolgelerK(T) {
    T = Math.min(Math.max(T, sinir.y[0]), sinir.y[1]);
    const i = indeks(T), a = rows[i], b = rows[i + 1];
    if (!b) return a.r;
    if (!ayniTopoloji(a, b)) return (T - a.T < b.T - T ? a : b).r;
    const t = (T - a.T) / (b.T - a.T);
    return a.r.map((r, k) => ({ p: r.p, x: [r.x[0] + t * (b.r[k].x[0] - r.x[0]), r.x[1] + t * (b.r[k].x[1] - r.x[1])] }));
  }

  /** Izgaradan ikili doğrusal ara değer; sadece o noktadaki bölgenin fazları, yeniden normalize */
  function oranlar(w, T) {
    const r = bolgeBul(bolgelerK(T), w);
    const i = indeks(T), a = rows[i], b = rows[Math.min(i + 1, rows.length - 1)];
    const t = b.T === a.T ? 0 : Math.min(Math.max((T - a.T) / (b.T - a.T), 0), 1);
    let j = 0;
    while (j < CG.length - 2 && CG[j + 1] <= w) j++;
    const u = Math.min(Math.max((w - CG[j]) / (CG[j + 1] - CG[j]), 0), 1);
    const fazlar = r.p.map((f) => {
      const deger = (row, jj) => (row.o[f] ? row.o[f][jj] : 0);
      const m = (1 - t) * ((1 - u) * deger(a, j) + u * deger(a, j + 1)) + t * ((1 - u) * deger(b, j) + u * deger(b, j + 1));
      // fazın kendi karbonu: fazın bulunduğu en yakın ızgara noktalarının ortalaması
      const cs = [];
      for (const [row, jj, ag] of [[a, j, (1 - t) * (1 - u)], [a, j + 1, (1 - t) * u], [b, j, t * (1 - u)], [b, j + 1, t * u]]) {
        const c = row.c[f] && row.c[f][jj];
        if (c != null) cs.push([c, ag + 1e-9]);
      }
      const wc = cs.length ? cs.reduce((s, [c, g]) => s + c * g, 0) / cs.reduce((s, [, g]) => s + g, 0) : null;
      return { f, oran: Math.max(m, 0), w: wc };
    });
    const top = fazlar.reduce((s, f) => s + f.oran, 0);
    if (top > 0) fazlar.forEach((f) => { f.oran /= top; });
    else fazlar.forEach((f) => { f.oran = 1 / fazlar.length; });
    if (r.p.length === 1) fazlar[0].w = w;
    return { r, fazlar };
  }

  /** İki bölge arasındaki ortak sınırın karbon değeri (yoksa null) */
  function ortakSinir(row, ka, kb) {
    for (let k = 0; k < row.r.length - 1; k++) {
      const p = key(row.r[k].p), q = key(row.r[k + 1].p);
      if ((p === ka && q === kb) || (p === kb && q === ka)) return row.r[k].x[1];
    }
    return null;
  }

  /** Dikey tarama: faz kümesi değişimleri, sınır eğrisinden ara değerli sıcaklıkla */
  function gecislerK(w) {
    const out = [];
    for (let i = 1; i < rows.length; i++) {
      const A = rows[i - 1], B = rows[i];
      const ra = bolgeBul(A.r, w), rb = bolgeBul(B.r, w);
      const ka = key(ra.p), kb = key(rb.p);
      if (ka === kb) continue;
      let T = 0.5 * (A.T + B.T);
      const xa = ortakSinir(A, ka, kb), xb = ortakSinir(B, ka, kb);
      if (xa != null && xb != null && xa !== xb && (xa - w) * (xb - w) <= 0) T = A.T + (w - xa) / (xb - xa) * (B.T - A.T);
      out.push({ T, alt: ra.p, ust: rb.p });
    }
    return out.map((g) => ({ ...g, ...gecisAdiK(g) }));
  }
  function gecisAdiK({ alt, ust }) {
    const yok = (f) => alt.includes(f) && !ust.includes(f), var_ = (f) => !alt.includes(f) && ust.includes(f);
    const kAlt = alt.filter((f) => KARBURLER.includes(f)), kUst = ust.filter((f) => KARBURLER.includes(f));
    // kod: program mantığı için sabit etiket (Ae1, Ae3, Aecm...); ad: ekranda görünen (dile göre)
    const parca = [];
    if (var_('G')) parca.push({ kod: 'Ae1', ad: 'Ae1', aciklama: t('gk.Ae1') });
    if (yok('A')) parca.push({ kod: 'Ae3', ad: 'Ae3', aciklama: t('gk.Ae3') });
    const asil = (p) => p.filter((f) => f !== 'MC');
    if (asil(kAlt).length && !asil(kUst).length) {
      parca.push({ kod: 'Aecm', ad: 'Aecm', aciklama: t(kUst.includes('MC') ? 'gk.Aecm.mc' : 'gk.Aecm') });
      if (kAlt.includes('MC') && !ust.includes('MC')) parca.push({ kod: 'MCcoz', ad: t('gk.cozunur', { f: 'MC' }), aciklama: '' });
    }
    else for (const f of kAlt) if (!ust.includes(f)) parca.push({ kod: f + 'coz', ad: t('gk.cozunur', { f: FAZ[f].kisa }), aciklama: '' });
    for (const f of kUst) if (!alt.includes(f)) parca.push({ kod: f + 'olus', ad: t('gk.olusur', { f: FAZ[f].kisa }), aciklama: '' });
    if (var_('L')) parca.push({ kod: 'solidus', ad: t('gecis.solidus'), aciklama: t('gecis.solidus.a') });
    if (!parca.length) return { kod: 'diger', ad: kisaAd(alt) + ' → ' + kisaAd(ust), aciklama: '' };
    return { kod: parca.map((p) => p.kod).join('+'), ad: parca.map((p) => p.ad).join(' + '), aciklama: parca.map((p) => p.aciklama).filter(Boolean).join(', '), etiketler: parca.map((p) => p.kod) };
  }

  /** Isıl işlem için kritik sıcaklıklar (detay.js ile ortak arayüz) */
  const kritikOnbellek = new Map();
  function kritik(w) {
    const anahtar = w.toFixed(4);
    if (kritikOnbellek.has(anahtar)) return kritikOnbellek.get(anahtar);
    const gs = gecislerK(w);
    const bul = (kod) => gs.find((g) => (g.etiketler || [g.kod]).includes(kod));
    const ae1 = bul('Ae1'), ae3 = bul('Ae3');
    // Acm ve hipo/hiper ayrımı: MC (VC, NbC...) hariç karbürler. MC çok kararlıdır ve tane
    // inceltici olarak östenitleme sıcaklığında bilerek çözünmeden bırakılır (ör. 51CrV4'te ~920 °C'ye kadar).
    const asilKarbur = (p) => p.some((f) => KARBURLER.includes(f) && f !== 'MC');
    const aecmL = gs.filter((g) => asilKarbur(g.alt) && !asilKarbur(g.ust));
    const aecm = aecmL.length ? aecmL[aecmL.length - 1] : null;
    // Hiperötektoid: ferrit bittiğinde sementit (Fe3C) hâlâ duruyorsa. Ferritten sonra çözünen alaşım karbürleri
    // (Cr, Mo) çeliği hiperötektoid yapmaz; ama tam östenitleme için onların da çözünmesi gerekir (tam).
    const ae3T = ae3 ? ae3.T : null;
    const hiper = ae3T != null && bolgeBul(bolgelerK(ae3T + 2), w).p.includes('C');
    const aecmT = aecm ? aecm.T : null;
    // Ae1 hesap aralığının altındaysa (yüksek Ni: dengede östenit 550 °C'de bile var) ilk satırda östenit bulunur
    const ae1Alt = !ae1 && bolgeBul(rows[0].r, w).p.includes('G');
    const sonuc = {
      ae1: ae1 ? ae1.T : null,
      ae1Alt,
      ae3: ae3T,
      aecm: aecmT,
      hipo: !hiper,
      // tam östenit (MC hariç) sıcaklığı: hipoda ferrit ve alaşım karbürlerinin ikisinin de bittiği yer
      tam: hiper ? aecmT : Math.max(ae3T ?? -Infinity, aecmT ?? -Infinity),
      kaynak: 'hesap',
    };
    if (!isFinite(sonuc.tam)) sonuc.tam = null;
    kritikOnbellek.set(anahtar, sonuc);
    return sonuc;
  }

  /* ---- çizim eki: çeliğin nominal karbonu ve bilgi etiketi ---- */
  function ciz() {
    // çeliğin nominal karbonu: tam boy çizgi yerine üst kenarda küçük işaret (seçim çizgisiyle karışmasın)
    if (etiket.C == null) return;   // elle girilen bileşimde nominal karbon yok
    const g = el('g', { 'clip-path': 'url(#kirp)' }, svg);
    const Cn = etiket.C, x = sx(Cn);
    el('path', { d: `M${x - 5},${M.t}L${x + 5},${M.t}L${x},${M.t + 8}Z`, class: 'nominal-isaret' }, g);
    const sola = x + 8 + (ad.length + 10) * 6.5 > W - M.r;
    el('text', { x: sola ? x - 8 : x + 8, y: M.t + 11, class: 'nominal-yazi', 'text-anchor': sola ? 'end' : 'start' }, g).textContent = `${ad} · ${fmtC(Cn)} C`;
  }

  /* ---- panel ---- */
  function panel() {
    const { C: w, T } = st;
    const { r, fazlar } = oranlar(w, T);
    const regs = bolgelerK(T);
    const alas = Object.entries(K.bilesim).filter(([e]) => e !== 'C').map(([e, v]) => `${ELEMENT_AD[e] || e} ${yuzde(fmt(v, 2))}`).join(' · ');
    const n = r.p.length;
    $('kBolge').innerHTML = `
      ${baslik(t('kart.nokta'), `${fmtC(w)} C · ${fmtT(T)}`)}
      <div class="buyuk">${kisaAd(r.p)}</div>
      <div class="kucuk soluk" style="margin-top:4px">${t('bolge.' + Math.min(n, 4))} · ${t('kesit.bolgeAciklama', { ad: esc(ad), alas })}</div>
      <div style="margin-top:8px;display:flex;gap:12px;flex-wrap:wrap">${r.p.map(chip).join('')}</div>`;

    const cubuk = fazlar.map((f) => `<div style="width:${f.oran * 100}%;background:var(--ph-${f.f})"></div>`).join('');
    const satirlar = fazlar.map((f) => `
      <div class="faz-satir"><span class="ad">${FAZ[f.f].ad}</span><span class="oran">${fmtP(f.oran)}</span>
      <span class="bilesim">${t('faz.karbon')}: <b>${f.w != null ? fmtC(f.w) : '—'}</b> C</span></div>`).join('');
    $('kOran').innerHTML = `${baslik(t('kart.oran'), t('kart.oran.meta.hesap'))}<div class="cubuk">${cubuk}</div>${satirlar}
      <div class="kucuk soluk" style="margin-top:6px">${t('kesit.oranNot', { izgara: `5 °C × ${fmtC(0.03)} C` })}</div>`;

    const gs = gecislerK(w);
    const k = kritik(w);
    const kare = (kod, T, not) => `<div class="kare ${T ? '' : 'yok'}"><b>${kod}</b><span>${T ? fmt(T, 0) + ' °C' : '—'}</span>${!T && not ? `<div class="kucuk soluk">${not}</div>` : ''}</div>`;
    const liste = gs.map((g) => `<tr><td><b>${g.ad}</b>${g.aciklama ? ` <span class="soluk">· ${g.aciklama}</span>` : ''}<br><span class="soluk">${kisaAd(g.alt)} → ${kisaAd(g.ust)}</span></td><td class="sag">≈ ${fmt(g.T, 0)} °C</td></tr>`).join('');
    $('kKritik').innerHTML = `
      ${baslik(t('kart.kritik'), t('kart.kritik.meta.hesap', { C: fmtC(w) }))}
      <div class="kritik-ust">${k.ae1Alt ? '<div class="kare"><b>Ae1</b><span>&lt; 550 °C</span></div>' : kare('Ae1', k.ae1)}${kare('Ae3', k.ae3)}${
        k.hipo && k.aecm != null && k.aecm > (k.ae3 ?? 0) + 1
          ? `<div class="kare"><b>${t('kare.karburCoz')}</b><span>${fmt(k.aecm, 0)} °C</span></div>`
          : kare('Aecm', k.hipo ? null : k.aecm, t('hipo.k'))}</div>
      <table class="liste">${liste}</table>
      <div class="kucuk soluk" style="margin-top:6px">${t('kesit.kritikNot')}</div>`;

    const yatay = regs.map((q) => `<tr class="${q.p.join() === r.p.join() && w >= q.x[0] - 1e-9 && w <= q.x[1] + 1e-9 ? 'aktif' : ''}"><td>${kisaAd(q.p)}</td><td class="sag">${fmtC(q.x[0])} – ${fmtC(q.x[1])}</td></tr>`).join('');
    $('kYatay').innerHTML = `${baslik(t('kart.yatay.kesit'), fmtT(T))}<table class="liste">${yatay}</table>
      <div class="kucuk soluk" style="margin-top:6px">${t('kesit.yatayNot')}</div>`;

    // A1 bandının altında denge fazları
    const Ta = k.ae1 ? Math.max(k.ae1 - 20, sinir.y[0]) : sinir.y[0];
    const alt = oranlar(w, Ta);
    $('kYapi').innerHTML = `${baslik(t('kart.yapi.kesit'), fmtT(Ta))}
      ${alt.fazlar.map((f) => `<div class="faz-satir"><span class="ad">${FAZ[f.f].ad}</span><span class="oran">${fmtP(f.oran)}</span></div>`).join('')}
      <div class="kucuk soluk" style="margin-top:6px">${t('kesit.yapiNot')}</div>`;
  }

  return { ad, anahtar, etiket, poly, sinir, bolgeler: bolgelerK, oranlar, gecisler: gecislerK, kritik, ciz, panel, K };
}

/** Kesiti (gerekirse dosyadan yükleyip) aç. Aynı alaşım açıksa sadece etiketi günceller. */
let kesitIstek = 0;
async function kesitAc(anahtar, etiket) {
  if (!kesitVar(anahtar)) return false;
  if (KAYNAK.alt && KAYNAK.alt.anahtar === anahtar) {
    if (KAYNAK.alt.etiket.ad !== etiket.ad || KAYNAK.alt.etiket.C !== etiket.C) {
      KAYNAK.alt = kesitKaynak(anahtar, etiket);
      lejantYaz(); guncelle();
    }
    return true;
  }
  const no = ++kesitIstek;
  // yavaş disk/bilgisayarda boş ekran kalmasın; hızlı yüklemede de gösterge yanıp sönmesin (120 ms eşiği)
  const gosterge = setTimeout(() => { if (no === kesitIstek) yuklemeGoster(t('kesit.yukleniyor', { ad: etiket.ad })); }, 120);
  try {
    await kesitYukle(anahtar);
  } catch (e) {
    clearTimeout(gosterge); yuklemeGizle();
    if (no === kesitIstek) bildir(t('kesit.yuklenemedi', { ad: etiket.ad }), 'hata', 8000);
    return false;
  }
  clearTimeout(gosterge); yuklemeGizle();
  if (no !== kesitIstek) return false;   // bu arada başka bir çelik seçildi
  KAYNAK.alt = kesitKaynak(anahtar, etiket);
  st.katman.emp = false;   // gerçek hesapta empirik çizgiler sadece karşılaştırma için: varsayılan kapalı
  lejantYaz();
  kaynakDegisti();
  return true;
}
function kesitKapat() {
  kesitIstek++;            // yolda olan yüklemeyi geçersiz kıl
  yuklemeGizle();
  if (!KAYNAK.alt) return;
  KAYNAK.alt = null;
  st.katman.emp = true;
  lejantYaz();
  kaynakDegisti();
}
function lejantYaz() {
  const fazlar = KAYNAK.alt
    ? [...new Set(KAYNAK.alt.poly.flatMap((P) => P.p))].sort((a, b) => Object.keys(FAZ).indexOf(a) - Object.keys(FAZ).indexOf(b))
    : ['A', 'G', 'D', 'L', 'C'];
  document.getElementById('lejant').innerHTML = fazlar
    .map((k) => `<span><i style="background:var(--ph-${k})"></i>${FAZ[k].ad}</span>`).join('') +
    `<span><i style="background:repeating-linear-gradient(45deg,var(--ph-A) 0 4px,var(--ph-G) 4px 8px)"></i>${t(KAYNAK.alt ? 'lejant.cokfaz' : 'lejant.cokfaz.ikili')}</span>` +
    (KAYNAK.alt ? `<span class="kaynak-rozet">${t('kesit.rozet', { ad: esc(KAYNAK.alt.ad) })}</span>` : '');
}
