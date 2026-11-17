'use strict';
/* Faz Atlası 2.0 sunucusu (backend/, FastAPI). Sunucu varsa çelik kütüphanesi (546 çelik, her normla arama),
   aile kesitleri, tıklanan noktanın faz oranları ve çelik sınıfına göre ısıl işlem rejimi oradan gelir.
   Sunucu yoksa (GitHub Pages, file://) aynı istekler "yerel API" ile statik dosyalardan karşılanır
   (backend/export_static.py: veri/kutuphane/celikler2.js + veri/aile/*.js). Anlık hesap gerektirenler (tıklanan
   noktanın faz oranları, elle girilen bileşimin rejimi) yerelde yoktur. Yerel dosyalar da yoksa uygulama eski
   63 çeliklik statik kütüphaneyle çalışır.

   Sunucu adresi: ?api=https://... > kayıtlı seçim (localStorage 'fec-api') > sayfanın kendi kökeni (http/https ise).
   app.js ve kesit.js'ten sonra, detay.js'ten önce yüklenir. */

const API = { taban: null, hazir: false, yerel: false, kancalar: [] };

API.taban = (() => {
  const url = new URLSearchParams(location.search).get('api');
  if (url) { try { localStorage.setItem('fec-api', url); } catch (e) { /* gizli pencere */ } return url.replace(/\/$/, ''); }
  try { const k = localStorage.getItem('fec-api'); if (k) return k.replace(/\/$/, ''); } catch (e) { /* gizli pencere */ }
  return location.protocol.startsWith('http') && !location.hostname.endsWith('.github.io') ? '' : null;
})();

async function apiIstek(yol, govde, sure = 30000) {
  if (API.yerel) return yerelIstek(yol, govde);
  const kontrol = new AbortController();
  const zaman = setTimeout(() => kontrol.abort(), sure);
  try {
    const r = await fetch(API.taban + yol, govde
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(govde), signal: kontrol.signal }
      : { signal: kontrol.signal });
    // durum: sunucu yanıt verdi ama hesap yapılamadı (5xx, 422) ile ağ hatasını ayırmak için
    if (!r.ok) throw Object.assign(new Error(`${r.status} ${yol}`), { durum: r.status });
    return await r.json();
  } finally {
    clearTimeout(zaman);
  }
}

/** Sunucu hazır olunca çağrılacaklar (detay.js arama ve kesit seçimini buna bağlar) */
function apiHazirOlunca(f) { if (API.hazir) f(); else API.kancalar.push(f); }

API.kontrol = (async () => {
  if (API.taban != null) {
    try {
      const h = await apiIstek('/api/v1/health', null, 2500);
      API.hazir = h.status === 'ok';
      API.elementler = h.elements;
    } catch (e) {
      API.hazir = false;
    }
  }
  if (!API.hazir) API.hazir = API.yerel = await yerelYukle();
  if (API.hazir) API.kancalar.splice(0).forEach((f) => f());
  return API.hazir;
})();

/* ---------- yerel API (sunucusuz) ---------- */
function scriptYukle(src) {
  return new Promise((ok, hata) => {
    const sc = document.createElement('script');
    sc.src = src;
    sc.onload = ok;
    sc.onerror = () => { sc.remove(); hata(new Error('yüklenemedi: ' + src)); };
    document.head.appendChild(sc);
  });
}
const YERELVERI = { celik: new Map(), aile: {}, bekleyen: {} };
async function yerelYukle() {
  try { await scriptYukle('veri/kutuphane/celikler2.js?v=24'); } catch (e) { return false; }
  const K = window.KUTUPHANE_V2;
  if (!K || !K.celikler) return false;
  for (const c of K.celikler) YERELVERI.celik.set(c.id, c);
  YERELVERI.aileler = K.aileler;
  return true;
}
window.AILE_YUKLE = (fid, veri) => { YERELVERI.aile[fid] = veri; };
/** Aile kesiti dosyası (veri/aile/<aile>.js) script olarak yüklenir; aynı aile için tek yükleme yapılır. */
function yerelAile(fid) {
  if (YERELVERI.aile[fid]) return Promise.resolve(YERELVERI.aile[fid]);
  if (!YERELVERI.bekleyen[fid]) {
    YERELVERI.bekleyen[fid] = scriptYukle(`veri/aile/${encodeURIComponent(fid)}.js`)
      .then(() => {
        if (!YERELVERI.aile[fid]) throw new Error('aile dosyası okunamadı: ' + fid);   // bozuk ya da eksik dosya
        return YERELVERI.aile[fid];
      })
      .finally(() => { delete YERELVERI.bekleyen[fid]; });
  }
  return YERELVERI.bekleyen[fid];
}

/* Norm adı arama: backend/faz_atlasi/library/designations.py (normalize, query_variants) ve search.py ile aynı kural */
const KIRIL = { Х: 'X', Н: 'N', Т: 'T', М: 'M', В: 'V', Ф: 'F', Б: 'B', Г: 'G', С: 'S', Ю: 'YU', Д: 'D', К: 'K', Р: 'R',
  А: 'A', Ц: 'C', Е: 'E', П: 'P', Ш: 'SH', У: 'U', Л: 'L' };
const ONEKLER = ['AISI', 'SAE', 'DIN', 'EN', 'WNR', 'WERKSTOFF', 'UNS', 'ASTM', 'ACI', 'JIS', 'GOST', 'BS'];
function normAd(s, gost) {
  let n = [...String(s).normalize('NFKC').toUpperCase()].map((h) => KIRIL[h] || h).join('').replace(/[^0-9A-Z]/g, '');
  return gost ? n.replace(/C/g, 'S') : n;
}
function aramaBicimleri(q) {
  const n = normAd(q), out = [n];
  for (const on of ONEKLER) if (n.startsWith(on) && n.length > on.length) out.push(n.slice(on.length));
  return [...new Set([...out, ...out.map((v) => normAd(v, true))].filter(Boolean))];
}
function yerelAra(q, limit) {
  const v = aramaBicimleri(q || '');
  const kiyas = (a, b) => { for (let i = 0; i < 4; i++) if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1; return 0; };
  const eslesme = new Map();
  for (const c of YERELVERI.celik.values()) {
    for (const [system, code, approx, norm] of c.adlar) {
      if (v.length && !v.some((x) => norm.includes(x))) continue;
      const derece = !v.length || v.includes(norm) ? 0 : v.some((x) => norm.startsWith(x)) ? 1 : 2;
      const anahtar = [derece, approx, norm.length, code];
      const eski = eslesme.get(c.id);
      if (!eski || kiyas(anahtar, eski.anahtar) < 0) eslesme.set(c.id, { anahtar, c, d: { system, code, approx: !!approx } });
    }
  }
  const sirali = [...eslesme.values()].sort((a, b) => kiyas(a.anahtar, b.anahtar));
  return {
    total: sirali.length,
    items: sirali.slice(0, limit).map(({ c, d }) => ({
      id: c.id, name: c.ad, standard_name: c.ad, matched: d, group: c.grup, group_en: c.grup_en, steel_class: c.sinif,
      alloy_family_id: c.aile, isopleth_available: !!(YERELVERI.aileler[c.aile] && YERELVERI.aileler[c.aile].kesit),
    })),
  };
}
function yerelCelik(c) {
  const adlar = {};
  for (const [system, code, approx] of c.adlar) (adlar[system] = adlar[system] || []).push({ system, code, approx: !!approx });
  return {
    id: c.id, standard_name: c.ad, designations: adlar, group: c.grup, group_en: c.grup_en, steel_class: c.sinif,
    standard_code: c.std, usage_tr: c.kul, usage_en: c.kul_en,
    composition: c.bil.map(([element, min, max, nominal]) => ({ element, min, max, nominal })),
    alloy_family_id: c.aile, family_parent_id: c.ust,
    isopleth_available: !!(YERELVERI.aileler[c.aile] && YERELVERI.aileler[c.aile].kesit),
    sources: c.kaynak, missing_elements: c.eksik,
  };
}
/** Sunucu yolunu yerel veriyle karşılar; yerelde yapılamayan istek hata verir (çağıran sunucusuz durumu gösterir). */
async function yerelIstek(yol, govde) {
  const [p, sorgu] = yol.split('?');
  const par = new URLSearchParams(sorgu || '');
  let m;
  if (p === '/api/v1/steels') return yerelAra(par.get('q'), +(par.get('limit') || 50));
  if ((m = p.match(/^\/api\/v1\/steels\/(\d+)(\/[\w-]+)?$/))) {
    const c = YERELVERI.celik.get(+m[1]);
    if (!c) throw new Error('404 ' + yol);
    if (!m[2]) return yerelCelik(c);
    if (m[2] === '/family-fit' && c.uyum) return { steel_id: c.id, family_id: c.aile, parent_family_id: c.ust, ...c.uyum };
    if (m[2] === '/heat-treatment') {
      if (c.rejim) return { steel_id: c.id, standard_name: c.ad, ...c.rejim };
      // export_static.py rejimi hesaplanamayan çeliği (çözücü yakınsamadı / karbon yok) boş bırakır
      throw Object.assign(new Error('rejim hesaplanamadı: ' + yol), { durum: 500 });
    }
    throw new Error('yerelde yok: ' + yol);
  }
  if ((m = p.match(/^\/api\/v1\/isopleth\/(.+)$/))) return yerelAile(decodeURIComponent(m[1]));
  if (p === '/api/v1/validation' && window.KUTUPHANE_V2.meta.dogrulama) return window.KUTUPHANE_V2.meta.dogrulama;
  throw new Error('sunucusuz yapılamaz: ' + yol);
}

/* ---------- tek nokta denge (tıklanan noktanın faz oranları) ----------
   Sürüklerken her karede istek atılmaz: son istenen noktalar, imleç durduktan 200 ms sonra gönderilir. */
const NOKTA = { sonuc: new Map(), yolda: new Set(), sira: new Map(), zaman: 0 };
const noktaAnahtar = (bil, w, T) => `${JSON.stringify(bil)}|${w.toFixed(4)}|${T.toFixed(1)}`;

/** Önbellekteki sonuç; yoksa sıraya alır ve null döner (gelince guncelle() çağrılır). */
function apiNokta(bilesim, w, T) {
  if (API.yerel) return { yerel: true };   // anlık CALPHAD hesabı sunucu ister
  const k = noktaAnahtar(bilesim, w, T);
  if (NOKTA.sonuc.has(k)) return NOKTA.sonuc.get(k);
  if (!NOKTA.yolda.has(k)) {
    NOKTA.sira.set(k, { composition: { ...bilesim, C: +w.toFixed(4) }, T: +T.toFixed(1) });
    clearTimeout(NOKTA.zaman);
    NOKTA.zaman = setTimeout(noktaGonder, 200);
  }
  return null;
}
function noktaGonder() {
  // sadece en son istenen birkaç nokta (panel + pin kartı + A1 altı yapı)
  const istekler = [...NOKTA.sira.entries()].slice(-4);
  NOKTA.sira.clear();
  for (const [k, govde] of istekler) {
    NOKTA.yolda.add(k);
    apiIstek('/api/v1/equilibrium/point', govde)
      .then((r) => { NOKTA.sonuc.set(k, r); })
      .catch(() => { NOKTA.sonuc.set(k, { hata: true }); })
      .finally(() => { NOKTA.yolda.delete(k); guncelle(); });
  }
}

/* ---------- ısıl işlem rejimi ---------- */
const REJIM = { anahtar: null, veri: null, bekliyor: false };
/** kaynak: { id } (kütüphane çeliği) ya da { bilesim } (elle girilen). Sonuç gelince guncelle(). */
function rejimIste(kaynak) {
  const anahtar = kaynak ? JSON.stringify(kaynak) : null;
  if (anahtar === REJIM.anahtar) return;
  REJIM.anahtar = anahtar;
  REJIM.veri = null;
  REJIM.bekliyor = !!kaynak && API.hazir;
  if (!REJIM.bekliyor) return;
  const istek = kaynak.id != null
    ? apiIstek(`/api/v1/steels/${kaynak.id}/heat-treatment`, null, 90000)
    : apiIstek('/api/v1/heat-treatment', { composition: kaynak.bilesim }, 90000);
  istek.then((r) => { if (REJIM.anahtar === anahtar) REJIM.veri = r; })
    // hesaplanamadi: hesap sunucuda denendi ve başarısız oldu (ağ hatası / zaman aşımı değil)
    .catch((e) => { if (REJIM.anahtar === anahtar) REJIM.veri = { hata: true, hesaplanamadi: e.durum >= 500 || e.durum === 422 }; })
    .finally(() => { if (REJIM.anahtar === anahtar) { REJIM.bekliyor = false; guncelle(); } });
}
/** A1/A3 dönüşümü olmayan rejim aktif mi (östenitik, dupleks, ferritik paslanmaz...) */
const donusumsuzRejim = () => !!(REJIM.veri && REJIM.veri.mode && REJIM.veri.mode !== 'transformation');

/* ---------- çelik–aile uyumu ----------
   Aile kesiti, ailenin bileşimiyle hesaplanır. Çeliğin kendi kritik sıcaklıkları ile kesittekiler arasındaki fark
   sunucuda ölçülür (çeliğin karbonunda; backend/faz_atlasi/calc/sapma.py); kesit.js bu çiftlerle sıcaklık eksenini
   çeliğe göre kaydırır. Ölçülmemiş çelikte ilk istek 10–30 s sürebilir. */
const UYUM = { id: null, veri: null };
function uyumIste(id) {
  if (id === UYUM.id) return;
  UYUM.id = id;
  UYUM.veri = null;
  if (id == null || !API.hazir) return;
  apiIstek(`/api/v1/steels/${id}/family-fit`, null, 120000)
    .then((r) => { if (UYUM.id === id) UYUM.veri = r; })
    .catch(() => { if (UYUM.id === id) UYUM.veri = { hata: true }; })
    .finally(() => { if (UYUM.id === id) kesitUyumDegisti(); });
}

/* ---------- ölçümle doğrulama özeti (güven etiketi) ----------
   Sınıf başına ölçülen Ac − hesaplanan Ae (backend/validate_measured.py); bir kez alınır. */
const DOGRULAMA = { veri: null };
apiHazirOlunca(() => {
  apiIstek('/api/v1/validation').then((r) => { DOGRULAMA.veri = r; celikBilgiYaz(); }).catch(() => {});
});

/* ---------- sunucudan gelen kesit: kesit.js'in beklediği biçime ---------- */
async function apiKesitYukle(aile) {
  const k = await apiIstek(`/api/v1/isopleth/${encodeURIComponent(aile)}`, null, 60000);
  return {
    api: true, aile,
    rows: k.rows,
    C: [0, k.C_max],
    bilesim: k.composition,
    ignored: k.ignored_elements || [],
  };
}
