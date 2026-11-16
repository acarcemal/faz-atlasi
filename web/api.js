'use strict';
/* Faz Atlası 2.0 sunucusu (backend/, FastAPI). Sunucu varsa çelik kütüphanesi (546 çelik, her normla arama),
   aile kesitleri, tıklanan noktanın faz oranları ve çelik sınıfına göre ısıl işlem rejimi oradan gelir.
   Sunucu yoksa (GitHub Pages, file://) uygulama statik veri dosyalarıyla eskisi gibi çalışır.

   Sunucu adresi: ?api=https://... > kayıtlı seçim (localStorage 'fec-api') > sayfanın kendi kökeni (http/https ise).
   app.js ve kesit.js'ten sonra, detay.js'ten önce yüklenir. */

const API = { taban: null, hazir: false, kancalar: [] };

API.taban = (() => {
  const url = new URLSearchParams(location.search).get('api');
  if (url) { try { localStorage.setItem('fec-api', url); } catch (e) { /* gizli pencere */ } return url.replace(/\/$/, ''); }
  try { const k = localStorage.getItem('fec-api'); if (k) return k.replace(/\/$/, ''); } catch (e) { /* gizli pencere */ }
  return location.protocol.startsWith('http') ? '' : null;
})();

async function apiIstek(yol, govde, sure = 30000) {
  const kontrol = new AbortController();
  const zaman = setTimeout(() => kontrol.abort(), sure);
  try {
    const r = await fetch(API.taban + yol, govde
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(govde), signal: kontrol.signal }
      : { signal: kontrol.signal });
    if (!r.ok) throw new Error(`${r.status} ${yol}`);
    return await r.json();
  } finally {
    clearTimeout(zaman);
  }
}

/** Sunucu hazır olunca çağrılacaklar (detay.js arama ve kesit seçimini buna bağlar) */
function apiHazirOlunca(f) { if (API.hazir) f(); else API.kancalar.push(f); }

API.kontrol = (async () => {
  if (API.taban == null) return false;
  try {
    const h = await apiIstek('/api/v1/health', null, 2500);
    API.hazir = h.status === 'ok';
    API.elementler = h.elements;
  } catch (e) {
    API.hazir = false;
  }
  if (API.hazir) API.kancalar.splice(0).forEach((f) => f());
  return API.hazir;
})();

/* ---------- tek nokta denge (tıklanan noktanın faz oranları) ----------
   Sürüklerken her karede istek atılmaz: son istenen noktalar, imleç durduktan 200 ms sonra gönderilir. */
const NOKTA = { sonuc: new Map(), yolda: new Set(), sira: new Map(), zaman: 0 };
const noktaAnahtar = (bil, w, T) => `${JSON.stringify(bil)}|${w.toFixed(4)}|${T.toFixed(1)}`;

/** Önbellekteki sonuç; yoksa sıraya alır ve null döner (gelince guncelle() çağrılır). */
function apiNokta(bilesim, w, T) {
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
    .catch(() => { if (REJIM.anahtar === anahtar) REJIM.veri = { hata: true }; })
    .finally(() => { if (REJIM.anahtar === anahtar) { REJIM.bekliyor = false; guncelle(); } });
}
/** A1/A3 dönüşümü olmayan rejim aktif mi (östenitik, dupleks, ferritik paslanmaz...) */
const donusumsuzRejim = () => !!(REJIM.veri && REJIM.veri.mode && REJIM.veri.mode !== 'transformation');

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
