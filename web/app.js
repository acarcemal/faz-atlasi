'use strict';
/* Fe–Fe3C dinamik faz diyagramı.
   Veri: veri/fe_c.js (hesap/diyagram_uret.py ile pycalphad'dan üretilir).
   Her satır bir sıcaklıktaki bölgeleri karbon ekseni boyunca verir; iki fazlı
   bölgenin uçları o sıcaklıktaki bağlantı çizgisinin (tie-line) uçlarıdır. */

const D = window.FE_C_DATA;
const ROWS = D.rows;
const INV = D.invariants;
const W_CEM = D.meta.W_Fe3C;
const NS = 'http://www.w3.org/2000/svg';

const FAZ = {
  A: { ad: t('faz.A'), kisa: 'α' },
  G: { ad: t('faz.G'), kisa: 'γ' },
  D: { ad: t('faz.D'), kisa: 'δ' },
  L: { ad: t('faz.L'), kisa: 'L' },
  C: { ad: t('faz.C'), kisa: 'Fe₃C' },
};
const key = (p) => p.join('+');
const kisaAd = (p) => p.map((f) => FAZ[f].kisa).join(' + ');

const GORUNUM = {
  tam:        { x: [0, W_CEM], y: [400, 1600] },
  celik:      { x: [0, 2.2],   y: [500, 1600] },
  otektoid:   { x: [0, 1.4],   y: [600, 1000] },
  ferrit:     { x: [0, 0.1],   y: [550, 950] },
  peritektik: { x: [0, 0.7],   y: [1360, 1560] },
};

/* detay.js gibi eklentilerin çizime ve panele bağlandığı yerler */
const KANCA = {
  ciz: [], panel: [],
  ust: [],        // seçim noktasının üstüne çizilenler (sabit noktalar)
  tik: [],        // (e, w, T, px, py) => true ise varsayılan tıklama yapılmaz
  uzerinde: [],   // (px, py, e) => true ise imleç bir öğenin üstünde, artı imleci çizilmez
  sagTik: [],     // (px, py, e) => true ise tarayıcı menüsü açılmaz
};

/* Alternatif veri kaynağı (kesit.js: alaşımlı çelik kesiti). null ise ikili Fe–C.
   Beklenen arayüz: { ad, anahtar, poly, sinir: {x, y}, bolgeler(T), oranlar(w, T), kritik(w), ciz(), panel() } */
const KAYNAK = { alt: null };
const ikili = () => !KAYNAK.alt;
const sinirX = () => KAYNAK.alt ? KAYNAK.alt.sinir.x : [0, W_CEM];
const sinirY = () => KAYNAK.alt ? KAYNAK.alt.sinir.y : [D.meta.T_min, D.meta.T_max];

const st = {
  C: 0.45, T: 780,
  view: { x: [...GORUNUM.tam.x], y: [...GORUNUM.tam.y] },
  hover: null,
  // görünür katmanlar (Detay modundaki katman düğmeleri)
  katman: { faz: true, bant: true, emp: true, etiket: true },
};

/* ---------- sayı biçimi ---------- */
// Türkçe: %0,45 · 1.200 °C   English: 0.45% · 1,200 °C
const fmt = (n, d = 2) => Number(n).toLocaleString(YEREL, { minimumFractionDigits: d, maximumFractionDigits: d });
const yuzde = (s) => (DIL === 'tr' ? '%' + s : s + '%');
const fmtC = (w) => yuzde(fmt(w, w < 0.1 ? 4 : w < 1 ? 3 : 2));
const fmtT = (T) => fmt(T, 0) + ' °C';
const fmtP = (f) => yuzde(fmt(f * 100, 1));
/* Sayı kutuları: ondalık ayırıcıyı bilgisayarın dili değil uygulamanın dili belirler (TR 0,45 · EN 0.45).
   Bu yüzden type="text" + inputmode="decimal"; okurken virgül de nokta da kabul edilir. */
const sayiYaz = (n) => (DIL === 'tr' ? String(n).replace('.', ',') : String(n));
const sayiOku = (s) => parseFloat(String(s).trim().replace(',', '.'));
// ↑/↓ ile artır-azalt (Shift ile 10 kat); data-adim kutunun adımı
document.addEventListener('keydown', (e) => {
  const k = e.target;
  if (!(k instanceof HTMLInputElement) || !k.dataset.adim || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return;
  e.preventDefault();
  const adim = +k.dataset.adim * (e.shiftKey ? 10 : 1) * (e.key === 'ArrowUp' ? 1 : -1);
  const once = isFinite(sayiOku(k.value)) ? sayiOku(k.value) : 0;
  const ondalik = (k.dataset.adim.split('.')[1] || '').length;
  k.value = sayiYaz(+Math.max(0, once + adim).toFixed(ondalik));
  k.dispatchEvent(new Event('input', { bubbles: true }));
});
/** Kullanıcının yazdığı metni (kayıtlı çelik adı) HTML'e güvenle basmak için */
const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
/** Kart başlığı: başlık + sağda küçük bağlam bilgisi (ⓘ ve katlama düğmesini bilgi.js ekler) */
const baslik = (ad, meta = '') => `<div class="kart-bas"><h3>${ad}</h3>${meta ? `<span class="meta">${meta}</span>` : ''}</div>`;

/* ---------- veri sorgusu ---------- */
function satirIndeks(T) {
  let lo = 0, hi = ROWS.length - 1;
  if (T <= ROWS[0].T) return 0;
  if (T >= ROWS[hi].T) return hi - 1;
  while (hi - lo > 1) {
    const m = (lo + hi) >> 1;
    if (ROWS[m].T <= T) lo = m; else hi = m;
  }
  return lo;
}
const ayniTopoloji = (a, b) => a.r.length === b.r.length && a.r.every((r, i) => key(r.p) === key(b.r[i].p));

/** Verilen sıcaklıkta bölgeler (komşu satırlar arasında doğrusal ara değer). */
function bolgeler(T) {
  T = Math.min(Math.max(T, ROWS[0].T), ROWS[ROWS.length - 1].T);
  const i = satirIndeks(T);
  const a = ROWS[i], b = ROWS[i + 1];
  if (!b) return a.r;
  if (!ayniTopoloji(a, b)) return (T - a.T < b.T - T ? a : b).r;
  const t = (T - a.T) / (b.T - a.T);
  return a.r.map((r, k) => ({ p: r.p, x: [r.x[0] + t * (b.r[k].x[0] - r.x[0]), r.x[1] + t * (b.r[k].x[1] - r.x[1])] }));
}
function bolgeBul(regs, w) {
  for (const r of regs) if (w >= r.x[0] - 1e-9 && w <= r.x[1] + 1e-9) return r;
  return regs[regs.length - 1];
}

/** (w, T) noktasındaki fazlar, oranları (kaldıraç kuralı) ve bileşimleri. */
function durum(w, T) {
  const regs = bolgeler(T);
  const r = bolgeBul(regs, w);
  if (r.p.length === 1) {
    return { regs, r, fazlar: [{ f: r.p[0], oran: 1, w: r.p[0] === 'C' ? W_CEM : w }] };
  }
  const [xl, xr] = r.x;
  const fr = xr - xl > 1e-12 ? (xr - w) / (xr - xl) : 0.5;
  return { regs, r, fazlar: [{ f: r.p[0], oran: fr, w: xl }, { f: r.p[1], oran: 1 - fr, w: xr }] };
}

/** Bir karbon değeri için dikey tarama: faz kümesinin değiştiği sıcaklıklar. */
function gecisler(w) {
  const out = [];
  let prev = ROWS[0], prevR = bolgeBul(prev.r, w);
  for (let i = 1; i < ROWS.length; i++) {
    const row = ROWS[i], r = bolgeBul(row.r, w);
    if (key(r.p) !== key(prevR.p)) {
      let T = 0.5 * (prev.T + row.T);
      // değişmez çizgi bu aralıktaysa onun sıcaklığını kullan
      const inv = Object.values(INV).find((v) => v.T >= prev.T - 1e-6 && v.T <= row.T + 1e-6);
      if (inv) T = inv.T;
      else if (ayniTopoloji(prev, row)) {
        for (let k = 0; k < prev.r.length; k++) for (const j of [0, 1]) {
          const xa = prev.r[k].x[j], xb = row.r[k].x[j];
          if ((xa - w) * (xb - w) <= 0 && xa !== xb) T = prev.T + (w - xa) / (xb - xa) * (row.T - prev.T);
        }
      }
      out.push({ T, alt: prevR.p, ust: r.p });
    }
    prev = row; prevR = r;
  }
  return out.map((g) => ({ ...g, ...gecisAdi(g) }));
}

function gecisAdi({ T, alt, ust }) {
  const a = key(alt), u = key(ust);
  const yakin = (v) => Math.abs(T - v.T) < 0.6;
  // kod: programın içinde kullanılan sabit ad; ad: ekranda görünen (dile göre)
  if (yakin(INV.otektoid)) return { kod: 'A1', ad: 'A1', aciklama: t('gecis.A1') };
  if (yakin(INV.otektik)) return { kod: 'otektik', ad: t('inv.otektik'), aciklama: 'L ⇄ γ + Fe₃C' };
  if (yakin(INV.peritektik)) return { kod: 'peritektik', ad: t('inv.peritektik'), aciklama: 'δ + L ⇄ γ' };
  if (a === 'A+G' && u === 'G') return { kod: 'A3', ad: 'A3', aciklama: t('gecis.A3') };
  if (a === 'G+C' && u === 'G') return { kod: 'Acm', ad: 'Acm', aciklama: t('gecis.Acm') };
  if (a === 'A+C' && u === 'A') return { kod: 'solvus', ad: t('gecis.solvus'), aciklama: t('gecis.solvus.a') };
  if (a === 'A' && u === 'A+G') return { kod: 'ag', ad: t('gecis.ag.bas'), aciklama: t('gecis.ag.bas.a') };
  if (a === 'G' && u === 'D+G') return { kod: 'gd1', ad: t('gecis.gd.bas'), aciklama: t('gecis.gd.bas.a') };
  if (a === 'D+G' && u === 'D') return { kod: 'gd2', ad: t('gecis.gd.bit'), aciklama: t('gecis.gd.bit.a') };
  if (u === 'L') return { kod: 'likidus', ad: t('gecis.likidus'), aciklama: t('gecis.likidus.a') };
  if (!alt.includes('L') && ust.includes('L')) return { kod: 'solidus', ad: t('gecis.solidus'), aciklama: t('gecis.solidus.a') };
  return { kod: 'diger', ad: kisaAd(alt) + ' → ' + kisaAd(ust), aciklama: '' };
}

/* ---------- çizim ---------- */
const svg = document.getElementById('svg');
const kutu = document.getElementById('cizim');
const M = { l: 62, r: 14, t: 12, b: 44 };
let W = 800, H = 600;
const el = (tag, attrs = {}, parent) => {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
};
const sx = (w) => M.l + (w - st.view.x[0]) / (st.view.x[1] - st.view.x[0]) * (W - M.l - M.r);
const sy = (T) => H - M.b - (T - st.view.y[0]) / (st.view.y[1] - st.view.y[0]) * (H - M.t - M.b);
const ix = (px) => st.view.x[0] + (px - M.l) / (W - M.l - M.r) * (st.view.x[1] - st.view.x[0]);
const iy = (py) => st.view.y[0] + (H - M.b - py) / (H - M.t - M.b) * (st.view.y[1] - st.view.y[0]);

/* Bölge poligonları: aynı faz kümesine ait satır parçalarını üst üste birleştir.
   Bir önceki satırdaki parçayla örtüşmeyen ya da araya boşluk giren parça yeni poligon başlatır. */
function poligonlar(rows) {
  const bitmis = [], acik = new Map();   // key -> [{p, sol, sag, sonT, sonX}]
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i], devam = new Map();
    for (const r of row.r) {
      const k = key(r.p);
      const adaylar = acik.get(k) || [];
      const P = adaylar.find((q) => q.sonI === i - 1 && r.x[0] <= q.sonX[1] + 1e-6 && r.x[1] >= q.sonX[0] - 1e-6 && !q.kullanildi);
      const hedef = P || { p: r.p, sol: [], sag: [] };
      hedef.kullanildi = true;
      hedef.sol.push([r.x[0], row.T]); hedef.sag.push([r.x[1], row.T]);
      hedef.sonI = i; hedef.sonX = r.x;
      if (!devam.has(k)) devam.set(k, []);
      devam.get(k).push(hedef);
    }
    for (const [k, liste] of acik) for (const q of liste) if (q.sonI !== i) bitmis.push(q);
    for (const liste of devam.values()) for (const q of liste) q.kullanildi = false;
    acik.clear();
    for (const [k, liste] of devam) acik.set(k, liste);
  }
  for (const liste of acik.values()) bitmis.push(...liste);
  return bitmis;
}
const POLY = poligonlar(ROWS);
const aktifPoly = () => KAYNAK.alt ? KAYNAK.alt.poly : POLY;
const desenId = (p) => 'd-' + p.join('_');

function adimSec(aralik, hedef) {
  const ham = aralik / hedef;
  const us = Math.pow(10, Math.floor(Math.log10(ham)));
  for (const k of [1, 2, 5, 10]) if (k * us >= ham) return k * us;
  return 10 * us;
}

function ciz() {
  W = kutu.clientWidth; H = kutu.clientHeight;
  if (W < M.l + M.r + 20 || H < M.t + M.b + 20) return;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.textContent = '';
  const defs = el('defs', {}, svg);
  const clip = el('clipPath', { id: 'kirp' }, defs);
  el('rect', { x: M.l, y: M.t, width: W - M.l - M.r, height: H - M.t - M.b }, clip);
  // iki fazlı bölgeler için iki renkli çizgili desen
  const desenler = new Set();
  for (const P of aktifPoly()) if (P.p.length > 1 && !desenler.has(desenId(P.p))) {
    desenler.add(desenId(P.p));
    const n = P.p.length, gen = 5;
    const pat = el('pattern', { id: desenId(P.p), width: n * gen, height: 10, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' }, defs);
    P.p.forEach((f, j) => el('rect', { x: j * gen, width: gen, height: 10, style: `fill:var(--ph-${f})` }, pat));
  }

  // bölgeler
  const gb = el('g', { 'clip-path': 'url(#kirp)' }, svg);
  for (const P of aktifPoly()) {
    const pts = [...P.sol, ...P.sag.slice().reverse()].map(([w, T]) => sx(w).toFixed(1) + ',' + sy(T).toFixed(1));
    const fill = P.p.length > 1 ? `url(#${desenId(P.p)})` : `var(--ph-${P.p[0]})`;
    el('polygon', { points: pts.join(' '), class: 'bolge', style: st.katman.faz ? `fill:${fill}` : 'fill:none' }, gb);
  }
  // kareli zemin
  const gx = adimSec(st.view.x[1] - st.view.x[0], 10), gy = adimSec(st.view.y[1] - st.view.y[0], 10);
  const kare = el('g', { class: 'izgara' }, svg);
  const ince = (s) => s / 5;
  for (const [adim, sinif] of [[ince(gx), 'kare-ince'], [gx, 'kare-kalin']]) {
    for (let w = Math.ceil(st.view.x[0] / adim) * adim; w <= st.view.x[1] + 1e-9; w += adim)
      el('line', { x1: sx(w), x2: sx(w), y1: M.t, y2: H - M.b, class: sinif }, kare);
  }
  for (const [adim, sinif] of [[ince(gy), 'kare-ince'], [gy, 'kare-kalin']]) {
    for (let T = Math.ceil(st.view.y[0] / adim) * adim; T <= st.view.y[1] + 1e-9; T += adim)
      el('line', { y1: sy(T), y2: sy(T), x1: M.l, x2: W - M.r, class: sinif }, kare);
  }

  // Fe3C dikey çizgisi
  const cTepe = Math.max(...POLY.filter((P) => P.p.includes('C')).flatMap((P) => P.sag.map((q) => q[1])));
  if (ikili()) el('line', { x1: sx(W_CEM), x2: sx(W_CEM), y1: sy(D.meta.T_min), y2: sy(cTepe), class: 'bolge', style: 'stroke-width:2.5' }, gb);

  // bölge etiketleri: bölgenin en geniş göründüğü satır
  const ge = el('g', { 'clip-path': 'url(#kirp)' }, svg);
  for (const P of st.katman.etiket ? aktifPoly() : []) {
    const yazi = kisaAd(P.p);
    const gerek = yazi.length * 7.5 + 10;
    let en = null;
    for (let i = 0; i < P.sol.length; i++) {
      const T = P.sol[i][1];
      if (T < st.view.y[0] + 8 * (st.view.y[1] - st.view.y[0]) / (H - M.t - M.b) || T > st.view.y[1]) continue;
      const a = Math.max(sx(P.sol[i][0]), M.l), b = Math.min(sx(P.sag[i][0]), W - M.r);
      const g = b - a;
      if (g > gerek && (!en || g > en.g * 1.15 || (g > en.g * 0.85 && Math.abs(i - P.sol.length / 2) < Math.abs(en.i - P.sol.length / 2)))) en = { g, i, a, b, T };
    }
    if (!en) continue;
    // dikeyde bölgenin ortası: aynı genişlik bandında orta satır
    const bant = [];
    for (let i = 0; i < P.sol.length; i++) {
      const a = Math.max(sx(P.sol[i][0]), M.l), b = Math.min(sx(P.sag[i][0]), W - M.r);
      const T = P.sol[i][1];
      if (b - a > gerek && T >= st.view.y[0] && T <= st.view.y[1]) bant.push(i);
    }
    const orta = bant.length ? bant[Math.floor(bant.length / 2)] : en.i;
    const a = Math.max(sx(P.sol[orta][0]), M.l), b = Math.min(sx(P.sag[orta][0]), W - M.r);
    el('text', { x: (a + b) / 2, y: sy(P.sol[orta][1]), class: 'etiket' }, ge).textContent = yazi;
  }

  // eksenler
  const ga = el('g', { class: 'eksen' }, svg);
  el('rect', { x: M.l, y: M.t, width: W - M.l - M.r, height: H - M.t - M.b, fill: 'none', stroke: 'var(--sinir)' }, ga);
  const ondalik = (s) => Math.max(0, -Math.floor(Math.log10(s) + 1e-9));
  for (let w = Math.ceil(st.view.x[0] / gx) * gx; w <= st.view.x[1] + 1e-9; w += gx) {
    el('line', { x1: sx(w), x2: sx(w), y1: H - M.b, y2: H - M.b + 5 }, ga);
    el('text', { x: sx(w), y: H - M.b + 18, 'text-anchor': 'middle' }, ga).textContent = fmt(w, ondalik(gx));
  }
  for (let T = Math.ceil(st.view.y[0] / gy) * gy; T <= st.view.y[1] + 1e-9; T += gy) {
    el('line', { x1: M.l - 5, x2: M.l, y1: sy(T), y2: sy(T) }, ga);
    el('text', { x: M.l - 8, y: sy(T) + 4, 'text-anchor': 'end' }, ga).textContent = fmt(T, 0);
  }
  el('text', { x: (M.l + W - M.r) / 2, y: H - 6, 'text-anchor': 'middle', class: 'baslik' }, ga).textContent = t('eksen.C');
  const yb = el('text', { x: 14, y: (M.t + H - M.b) / 2, 'text-anchor': 'middle', class: 'baslik', transform: `rotate(-90 14 ${(M.t + H - M.b) / 2})` }, ga);
  yb.textContent = t('eksen.T');

  // değişmez noktalar
  const gi = el('g', { 'clip-path': 'url(#kirp)' }, svg);
  const noktalar = [
    [INV.otektoid.G, INV.otektoid.T, t('inv.otektoid')],
    [INV.otektik.L, INV.otektik.T, t('inv.otektik')],
    [INV.peritektik.G, INV.peritektik.T, t('inv.peritektik')],
  ];
  for (const [w, T, ad] of ikili() ? noktalar : []) {
    el('circle', { cx: sx(w), cy: sy(T), r: 3.5, class: 'inv-nokta' }, gi);
    const yazi = `${ad} ${fmt(T, 0)} °C · ${fmtC(w)}`;
    const sola = sx(w) + 6 + yazi.length * 6 > W - M.r;
    el('text', { x: sx(w) + (sola ? -6 : 6), y: sy(T) + 14, class: 'inv-yazi', 'text-anchor': sola ? 'end' : 'start' }, gi).textContent = yazi;
  }

  for (const f of KANCA.ciz) f();

  // seçim
  const gs = el('g', { 'clip-path': 'url(#kirp)' }, svg);
  const d = ikili() ? durum(st.C, st.T) : { r: { p: [] } };
  if (KAYNAK.alt) KAYNAK.alt.ciz();
  el('line', { x1: sx(st.C), x2: sx(st.C), y1: M.t, y2: H - M.b, class: 'sec-cizgi' }, gs);
  el('line', { x1: M.l, x2: W - M.r, y1: sy(st.T), y2: sy(st.T), class: 'sec-cizgi sec-yatay' }, gs);
  if (d.r.p.length === 2) {
    el('line', { x1: sx(d.r.x[0]), x2: sx(d.r.x[1]), y1: sy(st.T), y2: sy(st.T), stroke: 'var(--vurgu)', 'stroke-width': 3 }, gs);
    for (const x of d.r.x) el('circle', { cx: sx(x), cy: sy(st.T), r: 4.5, class: 'sec-uc' }, gs);
  }
  el('circle', { cx: sx(st.C), cy: sy(st.T), r: 6, class: 'sec-nokta' }, gs);

  for (const f of KANCA.ust) f();

  hoverCiz();
  if (!document.body.classList.contains('hazir')) { document.body.classList.add('hazir'); yuklemeGizle(); }
}

/** İmleç (hover) katmanı: fare hareketinde sadece bu katman yeniden çizilir, diyagram ve panel değil */
function hoverCiz() {
  const eski = svg.querySelector('g.hover-katman');
  if (eski) eski.remove();
  if (!st.hover) return;
  const { w, T } = st.hover;
  const gh = el('g', { class: 'hover-katman' }, svg);
  el('line', { x1: sx(w), x2: sx(w), y1: M.t, y2: H - M.b, class: 'hover-cizgi' }, gh);
  el('line', { x1: M.l, x2: W - M.r, y1: sy(T), y2: sy(T), class: 'hover-cizgi' }, gh);
  const r = bolgeBul(KAYNAK.alt ? KAYNAK.alt.bolgeler(T) : bolgeler(T), w);
  const yazi = `${fmtC(w)} · ${fmtT(T)} · ${kisaAd(r.p)}`;
  const kw = yazi.length * 6.6 + 16;
  let x = sx(w) + 12, y = sy(T) - 32;
  if (x + kw > W - M.r) x = sx(w) - kw - 12;
  if (y < M.t) y = sy(T) + 12;
  const hk = el('g', { class: 'hover-kutu' }, gh);
  el('rect', { x, y, width: kw, height: 22, rx: 5 }, hk);
  el('text', { x: x + 8, y: y + 15 }, hk).textContent = yazi;
}
let hoverBekleyen = false;
function hoverPlanla() {
  if (hoverBekleyen) return;
  hoverBekleyen = true;
  requestAnimationFrame(() => { hoverBekleyen = false; hoverCiz(); });
}

/* ---------- bekleme göstergesi ve bildirimler ---------- */
const yuklemeKutu = document.getElementById('yukleme');
function yuklemeGoster(metin) {
  document.getElementById('yuklemeYazi').textContent = metin;
  yuklemeKutu.hidden = false;
}
function yuklemeGizle() { yuklemeKutu.hidden = true; }

const bildirimKutu = document.getElementById('bildirim');
let bildirimZaman = 0;
/** Köşede kısa bir bildirim (tur: 'bilgi' | 'hata') */
function bildir(metin, tur = 'bilgi', sure = 6000) {
  bildirimKutu.textContent = metin;
  bildirimKutu.dataset.tur = tur;
  bildirimKutu.hidden = false;
  clearTimeout(bildirimZaman);
  bildirimZaman = setTimeout(() => { bildirimKutu.hidden = true; }, sure);
}
bildirimKutu.addEventListener('click', () => { bildirimKutu.hidden = true; });
// beklenmeyen hatalar sessizce kaybolmasın; aynı anda yağmur gibi bildirim de çıkmasın
let sonHata = 0;
function hataYakala() {
  if (Date.now() - sonHata < 10000) return;
  sonHata = Date.now();
  yuklemeGizle();
  bildir(t('hata.genel'), 'hata', 8000);
}
window.addEventListener('error', hataYakala);
window.addEventListener('unhandledrejection', hataYakala);

/* ---------- panel ---------- */
const chip = (f) => `<span class="chip"><i style="background:var(--ph-${f})"></i>${FAZ[f].ad}</span>`;

function panel() {
  if (KAYNAK.alt) { KAYNAK.alt.panel(); for (const f of KANCA.panel) f(); return; }
  const { C: w, T } = st;
  const d = durum(w, T);

  // 1. bölge
  let uyari = '';
  for (const [k, rx] of [['otektoid', 'γ ⇄ α + Fe₃C'], ['otektik', 'L ⇄ γ + Fe₃C'], ['peritektik', 'δ + L ⇄ γ']]) {
    if (Math.abs(T - INV[k].T) < 1) uyari = `<div class="uyari">${t('uyari.degismez', { ad: t(`inv.${k}.k`), T: fmt(INV[k].T, 1), rx })}</div>`;
  }
  document.getElementById('kBolge').innerHTML = `
    ${baslik(t('kart.nokta'), `${fmtC(w)} C · ${fmtT(T)}`)}
    <div class="buyuk">${kisaAd(d.r.p)}</div>
    <div class="kucuk soluk" style="margin-top:4px">${t(d.r.p.length === 1 ? 'bolge.1' : 'bolge.2')} · ${sinif(w)}</div>
    <div style="margin-top:8px;display:flex;gap:12px;flex-wrap:wrap">${d.r.p.map(chip).join('')}</div>${uyari}`;

  // 2. oranlar
  const cubuk = d.fazlar.map((f) => `<div style="width:${f.oran * 100}%;background:var(--ph-${f.f})"></div>`).join('');
  const satirlar = d.fazlar.map((f) => `
    <div class="faz-satir"><span class="ad">${FAZ[f.f].ad}</span><span class="oran">${fmtP(f.oran)}</span>
    <span class="bilesim">${t('faz.karbon')}: <b>${fmtC(f.w)}</b> C</span></div>`).join('');
  let kaldirac = '';
  if (d.fazlar.length === 2) {
    const [a, b] = d.fazlar;
    kaldirac = `<div class="kucuk soluk" style="margin-top:6px">${t('kaldirac')}: ${FAZ[a.f].kisa} = (${fmt(b.w, 3)} − ${fmt(w, 3)}) / (${fmt(b.w, 3)} − ${fmt(a.w, 3)})</div>`;
  }
  document.getElementById('kOran').innerHTML = `${baslik(t('kart.oran'), t('kart.oran.meta'))}<div class="cubuk">${cubuk}</div>${satirlar}${kaldirac}`;

  // 3. kritik sıcaklıklar
  const gs = gecisler(w);
  const bul = (kod) => gs.find((g) => g.kod === kod);
  const kare = (kod, g, yokNot) => `<div class="kare ${g ? '' : 'yok'}"><b>${kod}</b><span>${g ? fmt(g.T, 0) + ' °C' : '—'}</span>${!g && yokNot ? `<div class="kucuk soluk">${yokNot}</div>` : ''}</div>`;
  const A1 = bul('A1'), A3 = bul('A3'), Acm = bul('Acm');
  const liste = gs.map((g) => `<tr><td><b>${g.ad}</b>${g.aciklama ? ` <span class="soluk">· ${g.aciklama}</span>` : ''}<br><span class="soluk">${kisaAd(g.alt)} → ${kisaAd(g.ust)}</span></td><td class="sag">${fmt(g.T, 1)} °C</td></tr>`).join('');
  document.getElementById('kKritik').innerHTML = `
    ${baslik(t('kart.kritik'), `${fmtC(w)} C`)}
    <div class="kritik-ust">${kare('A1', A1)}${kare('A3', A3, w > INV.otektoid.G ? t('hiper.k') : '')}${kare('Acm', Acm, w < INV.otektoid.G ? t('hipo.k') : '')}</div>
    <table class="liste">${liste}</table>
    <div class="kucuk soluk" style="margin-top:6px">${t('kritik.not')}</div>`;

  // 4. yatay: bu sıcaklıkta tüm bölgeler
  const yatay = d.regs.map((r) => `<tr class="${r === d.r ? 'aktif' : ''}"><td>${kisaAd(r.p)}</td><td class="sag">${fmtC(r.x[0])} – ${fmtC(r.x[1])}</td></tr>`).join('');
  document.getElementById('kYatay').innerHTML = `${baslik(t('kart.yatay'), fmtT(T))}<table class="liste">${yatay}</table>
    <div class="kucuk soluk" style="margin-top:6px">${t('yatay.not')}</div>`;

  // 5. yavaş soğuma sonrası yapı
  document.getElementById('kYapi').innerHTML = `${baslik(t('kart.yapi'), t('kart.yapi.meta'))}${yapi(w)}`;

  for (const f of KANCA.panel) f();
}

function sinif(w) {
  const e = INV.otektoid, l = INV.otektik;
  if (w < e.A) return t('sinif.saf');
  if (Math.abs(w - e.G) < 0.01) return t('sinif.otektoid');
  if (w < e.G) return t('sinif.hipo');
  if (w <= l.G) return t('sinif.hiper');
  if (Math.abs(w - l.L) < 0.02) return t('sinif.otektik');
  if (w < l.L) return t('sinif.hipootektik');
  return t('sinif.hiperotektik');
}

function yapi(w) {
  const e = INV.otektoid, l = INV.otektik;
  const wa = e.A, we = e.G, wc = W_CEM;
  const toplamA = (wc - w) / (wc - wa);
  const toplam = `<div class="kucuk soluk" style="margin-top:8px">${t('yapi.toplam', { a: fmtP(Math.max(0, Math.min(1, toplamA))), c: fmtP(Math.max(0, Math.min(1, 1 - toplamA))) })}</div>`;
  const s = (ad, f) => `<div class="faz-satir"><span class="ad">${ad}</span><span class="oran">${fmtP(f)}</span></div>`;
  const otektikNot = `<div class="kucuk soluk" style="margin-top:6px">${t('yapi.otektikNot')}</div>`;
  if (w < wa) return `<div>${s(t('yapi.ferrit'), 1)}</div><div class="kucuk soluk">${t('yapi.tersiyer')}</div>`;
  if (w < we) {
    const pa = (we - w) / (we - wa);
    return s(t('yapi.proferrit'), pa) + s(t('yapi.perlit'), 1 - pa) + toplam;
  }
  if (w <= l.G) {
    const pc = (w - we) / (wc - we);
    return s(t('yapi.prosementit'), pc) + s(t('yapi.perlit'), 1 - pc) + toplam;
  }
  if (w < l.L) {
    const pg = (l.L - w) / (l.L - l.G);
    return s(t('yapi.birincilG'), pg) + s(t('yapi.ledeburit'), 1 - pg) + otektikNot + toplam;
  }
  const pc = (w - l.L) / (wc - l.L);
  return s(t('yapi.birincilC'), pc) + s(t('yapi.ledeburit'), 1 - pc) + otektikNot + toplam;
}

/* ---------- etkileşim ---------- */
/** Görünüm aralığını veri sınırına kırp; kesişim yoksa sınırın tamamı */
function kesis(a, s) {
  const lo = Math.max(a[0], s[0]), hi = Math.min(a[1], s[1]);
  return hi - lo > 1e-9 ? [lo, hi] : [...s];
}
/** Veri kaynağı değişince görünümü ve seçimi yeni sınırlara uydur */
function kaynakDegisti() {
  st.view = { x: [...sinirX()], y: [...sinirY()] };
  document.querySelectorAll('.gorunum button').forEach((x) => x.classList.toggle('aktif', x.dataset.v === 'tam'));
  const [x0, x1] = sinirX(), [y0, y1] = sinirY();
  slC.min = x0; slC.max = x1; inC.max = x1;
  slT.min = y0; slT.max = y1; inT.min = y0; inT.max = y1;
  sec(st.C, st.T);
}
const inC = document.getElementById('inC'), slC = document.getElementById('slC');
const inT = document.getElementById('inT'), slT = document.getElementById('slT');

function sec(C, T, kaynak) {
  const [x0, x1] = sinirX(), [y0, y1] = sinirY();
  if (C != null && isFinite(C)) st.C = Math.min(Math.max(C, x0), x1);
  if (T != null && isFinite(T)) st.T = Math.min(Math.max(T, y0), y1);
  if (kaynak !== 'inC') inC.value = sayiYaz(+st.C.toFixed(st.C < 0.1 ? 4 : 3));
  if (kaynak !== 'inT') inT.value = sayiYaz(Math.round(st.T * 10) / 10);
  slC.value = st.C; slT.value = st.T;
  guncelle();
}
let bekleyen = false;
function guncelle() {
  if (bekleyen) return;
  bekleyen = true;
  requestAnimationFrame(() => { bekleyen = false; ciz(); panel(); });
}

inC.addEventListener('input', () => sec(sayiOku(inC.value), null, 'inC'));
inT.addEventListener('input', () => sec(null, sayiOku(inT.value), 'inT'));
// kutudan çıkınca değeri sınırlar içinde ve dilin biçiminde yeniden yaz
inC.addEventListener('blur', () => sec(st.C, null));
inT.addEventListener('blur', () => sec(null, st.T));
slC.addEventListener('input', () => sec(parseFloat(slC.value), null));
slT.addEventListener('input', () => sec(null, parseFloat(slT.value)));

function svgNokta(e) {
  const r = svg.getBoundingClientRect();
  return { px: e.clientX - r.left, py: e.clientY - r.top };
}
const icinde = ({ px, py }) => px >= M.l && px <= W - M.r && py >= M.t && py <= H - M.b;
let surukle = false;
svg.addEventListener('pointerdown', (e) => {
  const p = svgNokta(e);
  if (!icinde(p)) return;
  if (e.button === 2) return;
  if (KANCA.tik.some((f) => f(e, ix(p.px), iy(p.py), p.px, p.py))) return;
  surukle = true;
  svg.setPointerCapture(e.pointerId);
  sec(ix(p.px), iy(p.py));
});
svg.addEventListener('pointermove', (e) => {
  const p = svgNokta(e);
  if (surukle) { sec(Math.min(Math.max(ix(p.px), st.view.x[0]), st.view.x[1]), Math.min(Math.max(iy(p.py), st.view.y[0]), st.view.y[1])); return; }
  const oncekiPin = st.pinUstunde;
  const ustunde = KANCA.uzerinde.some((f) => f(p.px, p.py, e));
  st.hover = icinde(p) && !ustunde && e.pointerType === 'mouse' ? { w: ix(p.px), T: iy(p.py) } : null;
  // sabit noktanın vurgusu değiştiyse her şey yeniden çizilir; yoksa sadece imleç katmanı
  if (st.pinUstunde !== oncekiPin) guncelle(); else hoverPlanla();
});
svg.addEventListener('pointerup', () => { surukle = false; });
svg.addEventListener('pointerleave', (e) => { st.hover = null; KANCA.uzerinde.forEach((f) => f(-1, -1, e)); guncelle(); });
svg.addEventListener('contextmenu', (e) => {
  const p = svgNokta(e);
  if (KANCA.sagTik.some((f) => f(p.px, p.py, e))) e.preventDefault();
});

// klavye: diyagram odaktayken ok tuşları noktayı gezdirir (Shift ile 10 kat)
svg.addEventListener('keydown', (e) => {
  const k = e.shiftKey ? 10 : 1;
  const dC = (st.view.x[1] - st.view.x[0]) / 200 * k, dT = (st.view.y[1] - st.view.y[0]) / 400 * k;
  const yon = { ArrowLeft: [-dC, 0], ArrowRight: [dC, 0], ArrowUp: [0, dT], ArrowDown: [0, -dT] }[e.key];
  if (!yon) return;
  e.preventDefault();
  sec(st.C + yon[0], st.T + yon[1]);
});

svg.addEventListener('wheel', (e) => {
  const p = svgNokta(e);
  if (!icinde(p)) return;
  e.preventDefault();
  const k = Math.exp(e.deltaY * 0.0015);
  const w0 = ix(p.px), T0 = iy(p.py);
  const yeni = (a, b, m, lim, minAr) => {
    let lo = m - (m - a) * k, hi = m + (b - m) * k;
    if (hi - lo < minAr) { const c = (lo + hi) / 2; lo = c - minAr / 2; hi = c + minAr / 2; }
    if (hi - lo > lim[1] - lim[0]) return [...lim];
    if (lo < lim[0]) { hi += lim[0] - lo; lo = lim[0]; }
    if (hi > lim[1]) { lo -= hi - lim[1]; hi = lim[1]; }
    return [lo, hi];
  };
  st.view.x = yeni(st.view.x[0], st.view.x[1], w0, sinirX(), 0.005);
  st.view.y = yeni(st.view.y[0], st.view.y[1], T0, sinirY(), 10);
  document.querySelectorAll('.gorunum button').forEach((b) => b.classList.remove('aktif'));
  guncelle();
}, { passive: false });

document.querySelectorAll('.gorunum button').forEach((b) => b.addEventListener('click', () => {
  const g = GORUNUM[b.dataset.v];
  st.view = { x: kesis(g.x, sinirX()), y: kesis(g.y, sinirY()) };
  document.querySelectorAll('.gorunum button').forEach((x) => x.classList.toggle('aktif', x === b));
  guncelle();
}));

document.getElementById('lejant').innerHTML = Object.entries(FAZ)
  .map(([k, f]) => `<span><i style="background:var(--ph-${k})"></i>${f.ad}</span>`).join('') +
  `<span><i style="background:repeating-linear-gradient(45deg,var(--ph-A) 0 4px,var(--ph-G) 4px 8px)"></i>${t('lejant.cokfaz.ikili')}</span>`;

/* ---------- gece / gündüz modu ---------- */
const sistemKoyu = window.matchMedia('(prefers-color-scheme: dark)');
const koyuMu = () => (document.documentElement.dataset.theme || (sistemKoyu.matches ? 'dark' : 'light')) === 'dark';
const temaBtn = document.getElementById('temaBtn');
function temaYaz() {
  temaBtn.innerHTML = koyuMu()
    ? `<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="3.6"/><path d="M10 1.8v2M10 16.2v2M1.8 10h2M16.2 10h2M4.2 4.2l1.4 1.4M14.4 14.4l1.4 1.4M4.2 15.8l1.4-1.4M14.4 5.6l1.4-1.4"/></svg><span>${t('tema.gunduz')}</span>`
    : `<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M16.5 12.3A7 7 0 0 1 7.7 3.5a7 7 0 1 0 8.8 8.8z"/></svg><span>${t('tema.gece')}</span>`;
  temaBtn.setAttribute('aria-pressed', koyuMu());
}
temaBtn.addEventListener('click', () => {
  const yeni = koyuMu() ? 'light' : 'dark';
  document.documentElement.dataset.theme = yeni;
  try { localStorage.setItem('fec-tema', yeni); } catch (e) { /* gizli pencere */ }
  temaYaz(); guncelle();
});
sistemKoyu.addEventListener('change', () => { temaYaz(); guncelle(); });
temaYaz();

new ResizeObserver(guncelle).observe(kutu);
window.addEventListener('DOMContentLoaded', () => sec(st.C, st.T));
