'use strict';
/* Dil (Türkçe / English).
   Seçim önceliği: adres satırındaki ?lang=tr|en  >  kayıtlı seçim  >  tarayıcı dili (Türkçe değilse İngilizce).
   Bütün arayüz metinleri SOZLUK'tan gelir; t('anahtar', {parametre}) seçili dildeki metni verir.
   HTML'deki sabit metinler data-t (metin), data-t-title, data-t-aria, data-t-ph (placeholder) ile bağlanır.
   Dil değişince sayfa, o anki durum (nokta, mod, çelik, görünüm) korunarak yeniden yüklenir; böylece hiçbir yerde
   iki dil karışık kalmaz. */

const DIL = (() => {
  const url = new URLSearchParams(location.search).get('lang');
  if (url === 'tr' || url === 'en') return url;
  try { const k = localStorage.getItem('fec-dil'); if (k === 'tr' || k === 'en') return k; } catch (e) { /* gizli pencere */ }
  return (navigator.language || 'en').toLowerCase().startsWith('tr') ? 'tr' : 'en';
})();
document.documentElement.lang = DIL;
const YEREL = DIL === 'tr' ? 'tr-TR' : 'en-US';

const SOZLUK = { tr: {}, en: {} };
/** Sözlüğe toplu ekleme: { anahtar: [tr, en] } */
function sozlukEkle(nesne) {
  for (const [k, [tr, en]] of Object.entries(nesne)) { SOZLUK.tr[k] = tr; SOZLUK.en[k] = en; }
}
/** Seçili dildeki metin. {ad} biçimindeki yer tutucular parametrelerle doldurulur. */
function t(k, p = {}) {
  let s = SOZLUK[DIL][k];
  if (s == null) { s = SOZLUK.tr[k]; if (s == null) { console.warn('çeviri yok:', k); return k; } }
  return String(s).replace(/\{(\w+)\}/g, (_, n) => (p[n] != null ? p[n] : ''));
}

/* ------------------------------------------------------------------ */
/* Genel arayüz, diyagram ve ikili Fe–C paneli (app.js, index.html)    */
/* ------------------------------------------------------------------ */
sozlukEkle({
  // sayfa
  'sayfa.baslik': ['Faz Atlası · Fe–C', 'Faz Atlası · Fe–C phase diagram'],
  'marka.alt': ['Fe–C · ısıl işlem', 'Fe–C · heat treatment'],
  'mod.etiket': ['Çalışma modu', 'Mode'],
  'mod.faz': ['Faz diyagramı', 'Phase diagram'],
  'mod.detay': ['Isıl işlem & alaşım', 'Heat treatment & alloys'],
  'ust.yontem': ['Yöntem ve kaynaklar', 'Methods & sources'],
  'ust.yontem.ipucu': ['Hesap yöntemi, veritabanları ve kaynaklar', 'Calculation method, databases and references'],
  'ust.tema.ipucu': ['Gece / gündüz modu', 'Dark / light mode'],
  'tema.gunduz': ['Gündüz', 'Light'],
  'tema.gece': ['Gece', 'Dark'],
  'dil.ipucu': ['Dil: Türkçe / English', 'Language: Türkçe / English'],
  'alan.C.ipucu': ['Karbon (% ağırlık)', 'Carbon (wt%)'],
  'alan.C.birim': ['% ağ.', 'wt%'],
  'alan.C.kaydirici': ['Karbon kaydırıcı', 'Carbon slider'],
  'alan.T.ipucu': ['Sıcaklık (°C)', 'Temperature (°C)'],
  'alan.T.kaydirici': ['Sıcaklık kaydırıcı', 'Temperature slider'],
  'gorunum.etiket': ['Görünüm', 'View'],
  'gorunum.tam': ['Tamamı', 'Full'],
  'gorunum.celik': ['Çelik', 'Steel'],
  'gorunum.otektoid': ['Ötektoid', 'Eutectoid'],
  'gorunum.ferrit': ['α-ferrit', 'α-ferrite'],
  'gorunum.peritektik': ['Peritektik', 'Peritectic'],
  'diyagram.bilgi': ['Diyagram nasıl okunur?', 'How to read the diagram'],
  'diyagram.aria': ['Faz diyagramı. Tıklayarak ya da ok tuşlarıyla nokta seç.', 'Phase diagram. Click or use the arrow keys to pick a point.'],
  'diyagram.kart.aria': ['Faz diyagramı', 'Phase diagram'],
  'panel.aria': ['Seçilen noktanın özellikleri', 'Properties of the selected point'],
  'yukleme.diyagram': ['Diyagram hazırlanıyor…', 'Preparing diagram…'],
  'kapat': ['Kapat', 'Close'],
  'noscript': ['Faz Atlası bir web uygulamasıdır ve çalışmak için JavaScript gerektirir. Tarayıcında JavaScript\'i açıp sayfayı yenile.',
    'Faz Atlası is a web app and needs JavaScript. Please enable JavaScript in your browser and reload the page.'],
  'hata.genel': ['Beklenmeyen bir hata oluştu. Sorun sürerse sayfayı yenile.', 'Something went wrong. If the problem persists, reload the page.'],

  // fazlar
  'faz.A': ['α-ferrit', 'α-ferrite'],
  'faz.G': ['Östenit (γ)', 'Austenite (γ)'],
  'faz.D': ['δ-ferrit', 'δ-ferrite'],
  'faz.L': ['Sıvı (L)', 'Liquid (L)'],
  'faz.C': ['Sementit (Fe₃C)', 'Cementite (Fe₃C)'],
  'lejant.cokfaz.ikili': ['İki fazlı bölge (çizgili)', 'Two-phase field (hatched)'],

  // eksenler ve değişmez noktalar
  'eksen.C': ['Karbon (% ağırlık)', 'Carbon (wt%)'],
  'eksen.T': ['Sıcaklık (°C)', 'Temperature (°C)'],
  'inv.otektoid': ['Ötektoid', 'Eutectoid'],
  'inv.otektik': ['Ötektik', 'Eutectic'],
  'inv.peritektik': ['Peritektik', 'Peritectic'],
  'inv.otektoid.k': ['ötektoid', 'eutectoid'],
  'inv.otektik.k': ['ötektik', 'eutectic'],
  'inv.peritektik.k': ['peritektik', 'peritectic'],

  // geçişler (ikili)
  'gecis.A1': ['Ötektoid: γ ⇄ α + Fe₃C', 'Eutectoid: γ ⇄ α + Fe₃C'],
  'gecis.A3': ['Ferrit tamamen östenite döner', 'Ferrite fully transforms to austenite'],
  'gecis.Acm': ['Sementit östenitte tamamen çözünür', 'Cementite fully dissolves in austenite'],
  'gecis.solvus': ['Solvüs', 'Solvus'],
  'gecis.solvus.a': ['Fe₃C, α içinde çözünür', 'Fe₃C dissolves in α'],
  'gecis.ag.bas': ['α→γ başlar', 'α→γ start'],
  'gecis.ag.bas.a': ['α + γ bölgesine girilir', 'Enters the α + γ field'],
  'gecis.gd.bas': ['γ→δ başlar', 'γ→δ start'],
  'gecis.gd.bas.a': ['δ-ferrit oluşmaya başlar', 'δ-ferrite starts to form'],
  'gecis.gd.bit': ['γ→δ biter', 'γ→δ finish'],
  'gecis.gd.bit.a': ['Tamamen δ-ferrit', 'Fully δ-ferrite'],
  'gecis.likidus': ['Likidus', 'Liquidus'],
  'gecis.likidus.a': ['Tamamen sıvı', 'Fully liquid'],
  'gecis.solidus': ['Solidus', 'Solidus'],
  'gecis.solidus.a': ['Ergime başlar', 'Melting starts'],

  // panel (ikili)
  'kart.nokta': ['Seçilen nokta', 'Selected point'],
  'bolge.1': ['Tek fazlı bölge', 'Single-phase field'],
  'bolge.2': ['İki fazlı bölge', 'Two-phase field'],
  'uyari.degismez': ['Bu sıcaklık {ad} çizgisinde ({T} °C). Tam bu sıcaklıkta üç faz bir arada bulunur: {rx}. Oranlar çizginin hemen altı/üstü için verilir.',
    'This temperature lies on the {ad} line ({T} °C). Exactly at this temperature three phases coexist: {rx}. Fractions are given for just below/above the line.'],
  'sinif.saf': ['Ticari saf demir', 'Commercially pure iron'],
  'sinif.otektoid': ['Ötektoid çelik', 'Eutectoid steel'],
  'sinif.hipo': ['Hipoötektoid çelik', 'Hypoeutectoid steel'],
  'sinif.hiper': ['Hiperötektoid çelik', 'Hypereutectoid steel'],
  'sinif.otektik': ['Ötektik beyaz dökme demir', 'Eutectic white cast iron'],
  'sinif.hipootektik': ['Hipoötektik beyaz dökme demir', 'Hypoeutectic white cast iron'],
  'sinif.hiperotektik': ['Hiperötektik beyaz dökme demir', 'Hypereutectic white cast iron'],
  'kart.oran': ['Faz oranları', 'Phase fractions'],
  'kart.oran.meta': ['ağırlıkça', 'by weight'],
  'faz.karbon': ['Fazın kendi karbonu', 'Carbon in phase'],
  'kaldirac': ['Kaldıraç kuralı', 'Lever rule'],
  'kart.kritik': ['Kritik sıcaklıklar', 'Critical temperatures'],
  'hipo.k': ['hipoötektoid', 'hypoeutectoid'],
  'hiper.k': ['hiperötektoid', 'hypereutectoid'],
  'kritik.not': ['Isıtmada aşağıdan yukarı faz değişimleri (denge değerleri).', 'Phase changes on heating, bottom to top (equilibrium values).'],
  'kart.yatay': ['İzoterm sınırları', 'Isotherm boundaries'],
  'yatay.not': ['İki fazlı bölgelerde uçlar, o sıcaklıkta iki fazın kendi karbon oranlarıdır.', 'In two-phase fields the end points are the carbon contents of the two phases at this temperature.'],
  'kart.yapi': ['Yavaş soğuma sonrası yapı', 'Microstructure after slow cooling'],
  'kart.yapi.meta': ['A1 altı', 'below A1'],
  'yapi.toplam': ['A1\'in hemen altında toplam faz: α {a}, Fe₃C {c}', 'Total phases just below A1: α {a}, Fe₃C {c}'],
  'yapi.ferrit': ['Ferrit (α)', 'Ferrite (α)'],
  'yapi.tersiyer': ['Soğumada α\'dan az miktarda tersiyer Fe₃C çökebilir.', 'A small amount of tertiary Fe₃C may precipitate from α on cooling.'],
  'yapi.proferrit': ['Proötektoid ferrit', 'Proeutectoid ferrite'],
  'yapi.perlit': ['Perlit (α + Fe₃C)', 'Pearlite (α + Fe₃C)'],
  'yapi.prosementit': ['Proötektoid (ikincil) Fe₃C', 'Proeutectoid (secondary) Fe₃C'],
  'yapi.birincilG': ['Birincil γ (→ perlit + Fe₃C)', 'Primary γ (→ pearlite + Fe₃C)'],
  'yapi.ledeburit': ['Ledeburit (→ dönüşmüş ledeburit)', 'Ledeburite (→ transformed ledeburite)'],
  'yapi.birincilC': ['Birincil Fe₃C', 'Primary Fe₃C'],
  'yapi.otektikNot': ['Oranlar ötektik sıcaklığının hemen altındaki değerlerdir.', 'Fractions are for just below the eutectic temperature.'],
});

/* ------------------------------------------------------------------ */
/* Alaşımlı çelik kesitleri (kesit.js)                                 */
/* ------------------------------------------------------------------ */
sozlukEkle({
  'faz.K7': ['M₇C₃ karbür', 'M₇C₃ carbide'],
  'faz.K23': ['M₂₃C₆ karbür', 'M₂₃C₆ carbide'],
  'faz.K6': ['M₆C karbür', 'M₆C carbide'],
  'faz.MC': ['MC karbür (VC…)', 'MC carbide (VC…)'],
  'faz.M2C': ['M₂C karbür', 'M₂C carbide'],
  'lejant.cokfaz': ['Çok fazlı bölge (çizgili)', 'Multi-phase field (hatched)'],
  'gk.Ae1': ['Östenit oluşmaya başlar', 'Austenite starts to form'],
  'gk.Ae3': ['Ferrit biter', 'Ferrite disappears'],
  'gk.Aecm': ['Son karbür çözünür', 'Last carbide dissolves'],
  'gk.Aecm.mc': ['Son karbür çözünür (MC hariç)', 'Last carbide dissolves (except MC)'],
  'gk.cozunur': ['{f} çözünür', '{f} dissolves'],
  'gk.olusur': ['{f} oluşur', '{f} forms'],
  'bolge.3': ['Üç fazlı bölge', 'Three-phase field'],
  'bolge.4': ['Dört fazlı bölge', 'Four-phase field'],
  'kesit.bolgeAciklama': ['<b>{ad}</b> kesiti ({alas} sabit)', '<b>{ad}</b> isopleth ({alas} fixed)'],
  'kart.oran.meta.hesap': ['ağırlıkça · hesap', 'by weight · calculated'],
  'kesit.oranNot': ['Alaşımlı kesitte bağlantı çizgileri bu düzlemde durmaz; kaldıraç kuralı uygulanmaz. Oranlar doğrudan termodinamik hesaptan ({izgara} ızgaradan ara değer).',
    'In an alloy isopleth the tie-lines do not lie in the plane of the section, so the lever rule does not apply. Fractions come straight from the thermodynamic calculation (interpolated on a {izgara} grid).'],
  'kart.kritik.meta.hesap': ['{C} C · hesap', '{C} C · calculated'],
  'kare.karburCoz': ['Karbür çözünür', 'Carbides dissolve'],
  'kesit.kritikNot': ['Alaşımlı çelikte A1 tek çizgi değil, Ae1 ile Ae3 (hiperötektoidde ferritin bittiği sıcaklık) arasında üç fazlı bir banttır. Denge değerleri; ısıtmada ölçülen Ac değerleri birkaç derece yüksektir.',
    'In an alloy steel A1 is not a single line but a three-phase band between Ae1 and Ae3 (in hypereutectoid steels, the temperature at which ferrite disappears). Equilibrium values; Ac temperatures measured on heating are a few degrees higher.'],
  'kart.yatay.kesit': ['İzoterm bölgeleri', 'Isotherm fields'],
  'kesit.yatayNot': ['Kesitte bölge sınırları fazların kendi karbonu değildir (ikili diyagramdan farkı bu).',
    'In an isopleth the field boundaries are not the carbon contents of the phases (this is the key difference from the binary diagram).'],
  'kart.yapi.kesit': ['A1 bandı altında denge fazları', 'Equilibrium phases below the A1 band'],
  'kesit.yapiNot': ['Yavaş soğumada ferrit + karbürler (perlit içindeki sementit ve alaşım karbürleri). Hangi karbürün oluşacağı sıcaklığa ve süreye bağlıdır.',
    'Slow cooling gives ferrite + carbides (cementite in pearlite and alloy carbides). Which carbide actually forms depends on temperature and time.'],
  'kesit.yukleniyor': ['{ad} kesiti yükleniyor…', 'Loading {ad} isopleth…'],
  'kesit.yuklenemedi': ['{ad} kesiti yüklenemedi; empirik model gösteriliyor. Sayfayı yenileyip tekrar deneyebilirsin.',
    'Could not load the {ad} isopleth; showing the empirical model instead. Reload the page to try again.'],
  'kesit.rozet': ['Gerçek hesap: {ad} kesiti · MatCalc mc_fe + pycalphad', 'Calculated: {ad} isopleth · MatCalc mc_fe + pycalphad'],
});

/* ------------------------------------------------------------------ */
/* Isıl işlem modu (detay.js)                                          */
/* ------------------------------------------------------------------ */
sozlukEkle({
  'el.Mn': ['Mangan', 'Manganese'], 'el.Si': ['Silisyum', 'Silicon'], 'el.Cr': ['Krom', 'Chromium'], 'el.Ni': ['Nikel', 'Nickel'],
  'el.Mo': ['Molibden', 'Molybdenum'], 'el.V': ['Vanadyum', 'Vanadium'], 'el.W': ['Tungsten', 'Tungsten'], 'el.Cu': ['Bakır', 'Copper'],

  'bant.tavlama': ['Tam tavlama / Sertleştirme', 'Full annealing / Hardening'],
  'bant.tavlama.a': ['Hipo: A3 + 30–50 °C · Hiper: A1 + 30–50 °C', 'Hypo: A3 + 30–50 °C · Hyper: A1 + 30–50 °C'],
  'bant.normal': ['Normalizasyon', 'Normalizing'],
  'bant.normal.a': ['Tam östenit (hipo: A3, hiper: Acm; alaşımlıda karbürler de çözünmüş) + 50–70 °C',
    'Fully austenitic (hypo: A3, hyper: Acm; in alloy steels with carbides dissolved) + 50–70 °C'],
  'bant.kuresel': ['Küreselleştirme', 'Spheroidizing'],
  'bant.kuresel.a': ['A1 − 30 °C … A1 (uzun bekleme)', 'A1 − 30 °C … A1 (long hold)'],
  'bant.gerilim': ['Gerilim giderme', 'Stress relieving'],
  'bant.gerilim.a': ['550–650 °C (A1\'in en az 20 °C altı, faz dönüşümü yok)', '550–650 °C (at least 20 °C below A1, no phase change)'],
  'bantlar.lejant': ['Bantlar ({C} C için)', 'Windows (for {C} C)'],

  'ortam.firin': ['Fırında (tavlama)', 'Furnace cool (annealing)'],
  'ortam.hava': ['Havada (normalizasyon)', 'Air cool (normalizing)'],
  'ortam.yag': ['Yağda', 'Oil quench'],
  'ortam.su': ['Suda', 'Water quench'],

  'kart.alas': ['Çelik ve alaşım', 'Steel & alloy'],
  'kart.alas.meta': ['% ağırlık', 'wt%'],
  'ara.ph': ['Çelik ara: ad, numara ya da AISI (ör. 4140, 1.7225, yay)', 'Search steel: grade, number or AISI (e.g. 4140, 1.7225, spring)'],
  'ara.aria': ['Çelik ara', 'Search steel'],
  'ara.bos': ['Eşleşen çelik yok. Elementleri aşağıya girip kendi çeliğini kaydedebilirsin.', 'No matching steel. Enter the elements below and save your own.'],
  'hesap.var': ['hesap', 'calc'],
  'hesap.var.ipucu': ['Gerçek hesap (CALPHAD kesiti) hazır', 'Calculated CALPHAD isopleth available'],
  'kayitli': ['Kayıtlı', 'Saved'],
  'kayitli.aciklama': ['senin girdiğin bileşim', 'your own composition'],
  'kayit.sil': ['Kayıtlı çeliği sil', 'Delete saved steel'],
  'kayit.ph': ['Bileşime ad ver (ör. Atölye 4140)', 'Name this composition (e.g. Shop 4140)'],
  'kayit.adYok': ['Kaydetmek için bir ad yaz.', 'Enter a name to save.'],
  'kayit.kaydedildi': ['"{ad}" kaydedildi (C {C}). Arama listesinde en üstte; bu tarayıcıda saklanır.', '"{ad}" saved (C {C}). It appears at the top of the search list and is stored in this browser.'],
  'kayit.guncellendi': ['"{ad}" güncellendi (C {C}). Arama listesinde en üstte; bu tarayıcıda saklanır.', '"{ad}" updated (C {C}). It appears at the top of the search list and is stored in this browser.'],
  'kaydet': ['Kaydet', 'Save'],
  'sifirla': ['Sıfırla', 'Reset'],
  'celik.aralik': ['Standart aralık: {aralik}. Hesapta aralığın ortası (tipik değer) kullanılır.', 'Standard range: {aralik}. Calculations use the mid-range (typical) value.'],
  'gercek.baslik': ['Gerçek hesap (CALPHAD kesiti)', 'Calculated (CALPHAD isopleth)'],
  'gercek.var': ['{ad} için hesaplanmış kesit var (MatCalc mc_fe + pycalphad).', 'A calculated isopleth is available for {ad} (MatCalc mc_fe + pycalphad).'],
  'gercek.sirada': ['{ad} için kesit henüz hesaplanmadı; şimdilik empirik model kullanılıyor.', 'No isopleth has been calculated for {ad} yet; using the empirical model for now.'],
  'gercek.yok': ['Bu bileşim için hesaplanmış kesit yok; empirik model kullanılıyor.', 'No calculated isopleth for this composition; using the empirical model.'],
  'gercek.ipucu': ['Kütüphaneden bir çelik seçince diyagram o çeliğin hesaplanmış kesitine geçer.', 'Pick a steel from the library to switch to its calculated isopleth.'],
  'girilen.bilesim': ['Girilen bileşim', 'Custom composition'],
  'bu.bilesim': ['Bu bileşim', 'This composition'],
  'gamajen.ipucu': ['gamajen (östenit yapıcı)', 'austenite stabilizer (γ-former)'],
  'alfajen.ipucu': ['alfajen (ferrit yapıcı)', 'ferrite stabilizer (α-former)'],
  'gamajen.aciklama': ['gamajen: γ alanını genişletir, A1\'i düşürür', 'γ-former: expands the γ field, lowers A1'],
  'alfajen.aciklama': ['alfajen: α alanını genişletir, A1\'i yükseltir', 'α-former: expands the α field, raises A1'],

  'katmanlar': ['Katmanlar', 'Layers'],
  'katman.faz': ['Faz renkleri', 'Phase colors'],
  'katman.bant': ['Isıl işlem bantları', 'Heat-treatment windows'],
  'katman.emp': ['Empirik çizgiler (A1′, A3′, Acm′)', 'Empirical lines (A1′, A3′, Acm′)'],
  'katman.etiket': ['Bölge adları', 'Field labels'],
  'katman.empNot': ['Empirik çizgiler alaşım elementi girilince açılır (alaşımsızken hesaplanan sınırlarla aynıdır).',
    'Empirical lines become available once alloying elements are entered (without alloying they coincide with the calculated boundaries).'],

  'uyari.andrewsC': ['C = {C}: Andrews formülleri C ≤ {sinir} için türetildi.', 'C = {C}: the Andrews equations were derived for C ≤ {sinir}.'],
  'uyari.element': ['{e} = {deger}: yaklaşık geçerlilik sınırı {sinir}.', '{e} = {deger}: approximate validity limit is {sinir}.'],
  'not.dokme': ['Bu bileşim dökme demir aralığında (C > {C}); çelik ısıl işlem pencereleri (tavlama, sertleştirme, normalizasyon, küreselleştirme) uygulanmaz. Gerilim giderme dökme demirde de yapılır.',
    'This composition is in the cast-iron range (C > {C}); steel heat-treatment windows (annealing, hardening, normalizing, spheroidizing) do not apply. Stress relieving is also used for cast irons.'],
  'kare.dokme': ['Dökme demir', 'Cast iron'],
  'dokme.k': ['çelik aralığı dışında', 'outside the steel range'],
  'not.normalSolidus': ['Normalizasyon penceresi verilmedi: tam östenit + 50–70 °C, katılaşma başlangıcına ({T} °C) {pay} °C\'den fazla yaklaşıyor (aşırı ısınma ve tane sınırı ergimesi riski).',
    'No normalizing window: full austenite + 50–70 °C comes within {pay} °C of the solidus ({T} °C), risking overheating and grain-boundary melting.'],
  'not.gerilimA1': ['A1 ({A1} °C) düşük olduğu için gerilim giderme üst sınırı A1 − {pay} °C\'ye çekildi; daha yükseği kısmi östenitleşme demektir.',
    'Because A1 is low ({A1} °C), the stress-relieving upper limit is capped at A1 − {pay} °C; going higher would partly re-austenitize the steel.'],
  'not.gerilimYok': ['Denge A1\'i 550 °C\'nin altında olduğu için gerilim giderme penceresi verilmedi; sıcaklığı çeliğin veri sayfasından alın (genelde son temperleme sıcaklığının altında).',
    'No stress-relieving window: the equilibrium A1 is below 550 °C. Take the temperature from the steel\'s data sheet (usually below the final tempering temperature).'],
  'uyari.msEmpirik': ['Ms ve martenzit sertliği hâlâ empirik (C ≤ {sinir} için türetildi).', 'Ms and martensite hardness are still empirical (derived for C ≤ {sinir}).'],

  'kart.islem': ['Isıl işlem sıcaklıkları', 'Heat treatment'],
  'kaynak.hesap': ['gerçek hesap', 'calculated'],
  'kaynak.empirik': ['empirik', 'empirical'],
  'kaynak.ikili': ['ikili Fe–C', 'binary Fe–C'],
  'gk.Ae1.k': ['östenit başlar', 'austenite starts'],
  'gk.Ae3.k': ['ferrit biter', 'ferrite gone'],
  'gk.Aecm.k': ['son karbür çözünür', 'last carbide dissolves'],
  'kare.A1ustu': ['A1 bandı üstü', 'Top of A1 band'],
  'kare.alasimKarburu': ['alaşım karbürü', 'alloy carbides'],
  'kare.sinif': ['Sınıf', 'Class'],
  'kare.hipo': ['Hipo', 'Hypo'],
  'kare.otektoidC': ['Ötektoid C', 'Eutectoid C'],
  'not.yuksekNi': ['Yüksek Ni: dengede östenit 550 °C\'nin (hesap aralığı) altında da kararlıdır; pratikte bu dönüşüm çok yavaştır.',
    'High Ni: at equilibrium, austenite is stable even below 550 °C (the calculated range); in practice this transformation is extremely sluggish.'],
  'not.karburCozunme': ['Ferrit bittikten sonra Cr/Mo karbürleri {T} °C\'ye kadar östenitte çözünmeden kalır. Karbürlerin tamamen çözünmesi (en yüksek sertleşebilirlik) isteniyorsa östenitleme {T30} °C\'nin üstünde yapılmalıdır; üretici tablolarının daha yüksek sıcaklık önermesinin sebebi budur.',
    'Once the ferrite is gone, Cr/Mo carbides persist in the austenite up to {T} °C. For complete carbide dissolution (maximum hardenability), austenitize above {T30} °C — which is why steel suppliers recommend higher temperatures.'],
  'not.empirikKarsilastirma': ['Empirik (Andrews) karşılaştırma: A1′ {A1} °C · {ikinci} °C (Katmanlar → Empirik çizgiler ile noktalı olarak görülebilir)',
    'Empirical (Andrews) comparison: A1′ {A1} °C · {ikinci} °C (show as dotted lines via Layers → Empirical lines)'],
  'not.hiperSertlestirme': ['Hiperötektoidde sertleştirme <b>Acm üstüne çıkılmadan</b> A1 + 30–50 °C\'de yapılır: Acm üstü tane irileşmesi, fazla kalıntı östenit ve çatlama riski getirir. Çözünmemiş Fe₃C aşınma direncine katkı verir.',
    'Hypereutectoid steels are hardened from A1 + 30–50 °C, <b>without going above Acm</b>: austenitizing above Acm coarsens the grain, increases retained austenite and raises the risk of quench cracking. Undissolved Fe₃C adds to wear resistance.'],
  'not.ureticiEmpirik': ['Not: Cr, Mo, V gibi karbür yapıcılar içeren çeliklerde karbürlerin çözünmesi için üretici tabloları genelde bu bantların 20–40 °C üstünü önerir (ör. 42CrMo4 sertleştirme 820–860 °C). Kesin değer için çeliğin veri sayfasına bakılmalı.',
    'Note: for steels with carbide formers such as Cr, Mo and V, supplier data sheets usually recommend 20–40 °C above these windows to dissolve the carbides (e.g. 42CrMo4 hardening at 820–860 °C). Always check the steel\'s data sheet.'],
  'not.ureticiHesap': ['Bantlar denge değerlerinden çizilir. Üretici tabloları karbürlerin çözünme hızı için genelde biraz daha yüksek sıcaklık önerir (ör. 42CrMo4 sertleştirme 820–860 °C).',
    'Windows are drawn from equilibrium values. Supplier data sheets usually recommend slightly higher temperatures so the carbides dissolve fast enough (e.g. 42CrMo4 hardening at 820–860 °C).'],
  'not.alasimKaymasi': ['Alaşım kayması: ΔA1 = {dA1} °C, ΔA3 (saf Fe) = {dA3} °C (Andrews katsayıları), ötektoid C {we0} → {we} (Bain). Noktalı çizgiler.',
    'Alloy shift: ΔA1 = {dA1} °C, ΔA3 (pure Fe) = {dA3} °C (Andrews coefficients), eutectoid C {we0} → {we} (Bain). Shown as dotted lines.'],

  'kart.sogu': ['Soğuma ve sertleşme', 'Cooling & hardening'],
  'sb.dusuk': ['düşük', 'low'], 'sb.orta': ['orta', 'medium'], 'sb.yuksek': ['yüksek', 'high'], 'sb.cokYuksek': ['çok yüksek', 'very high'],
  'sogu.Ms': ['Ms (martenzit başlangıcı, Andrews)', 'Ms (martensite start, Andrews)'],
  'sogu.Mf': ['Mf (yaklaşık, Ms − 215)', 'Mf (approx., Ms − 215)'],
  'sogu.martenzit': ['Oda sıcaklığında martenzit (Koistinen–Marburger)', 'Martensite at room temperature (Koistinen–Marburger)'],
  'sogu.kalinti': ['Kalıntı östenit (oda sıcaklığı)', 'Retained austenite (room temperature)'],
  'sogu.hrc': ['Tam martenzit sertliği (Hodge–Orehoski)', 'As-quenched hardness, 100% martensite (Hodge–Orehoski)'],
  'sogu.DI': ['İdeal kritik çap D<sub>I</sub> (ASTM A255, tane 7)', 'Ideal critical diameter D<sub>I</sub> (ASTM A255, grain size 7)'],
  'sogu.not': ['Yapı tahmini ~25 mm kesit, {cizgi} üstünden östenitlenmiş parça için kaba bir yönlendirmedir; gerçek sonuç kesite ve CCT diyagramına bağlıdır.',
    'The predicted structure is a rough guide for a ~25 mm section austenitized above {cizgi}; the actual result depends on section size and the steel\'s CCT diagram.'],
  'sogu.dokme': ['Ms, martenzit sertliği ve sertleşebilirlik bağıntıları çelikler için türetildi; dökme demirde verilmez. Dökme demirin yapısı (gri, beyaz, küresel grafitli) bileşime, aşılamaya ve döküm soğuma hızına bağlıdır.',
    'The Ms, martensite hardness and hardenability relations were derived for steels and are not given for cast irons. A cast iron\'s structure (grey, white, ductile) depends on composition, inoculation and the cooling rate in the mould.'],

  'sy.kalinti': ['Kalıntı östenit yüksek ({oran}); sıfıraltı işlem düşünülebilir.', 'Retained austenite is high ({oran}); consider a sub-zero treatment.'],
  'sy.catlak': ['Çatlama/çarpılma riski yüksek; hemen temperleme şart.', 'High risk of cracking and distortion; temper immediately.'],
  'sy.temper': ['Su verme sonrası temperleme gerekir.', 'Temper after quenching.'],
  'sy.martenzit': ['Martenzit', 'Martensite'],
  'sy.artiKalinti': ['+ kalıntı östenit', '+ retained austenite'],
  'sy.kabaPerlit.ferrit': ['Proötektoid ferrit + kaba perlit', 'Proeutectoid ferrite + coarse pearlite'],
  'sy.kabaPerlit.sementit': ['Tane sınırlarında proötektoid Fe₃C ağı + kaba perlit', 'Grain-boundary proeutectoid Fe₃C network + coarse pearlite'],
  'sy.kabaPerlit.yok': ['Kaba perlit', 'Coarse pearlite'],
  'sy.firin.a': ['Çok yavaş soğuma: dengeye en yakın yapı. En düşük sertlik, en iyi işlenebilirlik (hiperötektoidde Fe₃C ağı işlenebilirliği bozar; küreselleştirme tercih edilir).',
    'Very slow cooling: the structure closest to equilibrium. Lowest hardness and best machinability (in hypereutectoid steels the Fe₃C network hurts machinability; spheroidizing is preferred).'],
  'sy.havaSertlesen': ['Beynit / martenzit (havada sertleşen)', 'Bainite / martensite (air-hardening)'],
  'sy.havaSertlesen.a': ['Sertleşebilirlik çok yüksek: havada bile perlit oluşmadan dönüşüm aşağı kayar.', 'Very high hardenability: even in still air the transformation is pushed below the pearlite range.'],
  'sy.incePerlit.ferrit': ['Proötektoid ferrit + ince perlit', 'Proeutectoid ferrite + fine pearlite'],
  'sy.incePerlit.sementit': ['Tane sınırlarında proötektoid Fe₃C ağı + ince perlit', 'Grain-boundary proeutectoid Fe₃C network + fine pearlite'],
  'sy.incePerlit.yok': ['İnce perlit', 'Fine pearlite'],
  'sy.hava.a': ['Normalizasyon: tavlamaya göre daha ince ve homojen yapı, biraz daha yüksek mukavemet ve tokluk. Proötektoid faz oranı dengeye göre azalır.',
    'Normalizing: a finer, more uniform structure than annealing, with somewhat higher strength and toughness. The proeutectoid fraction is lower than at equilibrium.'],
  'sy.yagYeterli': ['Sertleşebilirlik yağda bu kesiti sertleştirmeye yeterli.', 'Hardenability is sufficient to through-harden this section in oil.'],
  'sy.martenzitBeynit': ['Martenzit + beynit / ince perlit', 'Martensite + bainite / fine pearlite'],
  'sy.yagKismi.a': ['Yüzey martenzit, çekirdekte beynit/ince perlit beklenir (kesit büyüdükçe artar).', 'Expect martensite at the surface and bainite/fine pearlite in the core (more so in larger sections).'],
  'sy.yagYetersiz': ['İnce perlit / beynit, yüzeyde kısmi martenzit', 'Fine pearlite / bainite, partial martensite at the surface'],
  'sy.yagYetersiz.a': ['Sadece karbonlu, düşük sertleşebilirlik: yağ bu kesit için yavaş kalır.', 'Plain carbon steel with low hardenability: an oil quench is too slow for this section.'],
  'sy.dusukC': ['Düşük karbonlu (lata) martenzit + ferrit', 'Low-carbon (lath) martensite + ferrite'],
  'sy.dusukC.a': ['Karbon düşük olduğu için sertlik sınırlı kalır; bu çelikler genelde sementasyonla sertleştirilir.', 'With so little carbon the hardness stays limited; these steels are usually case-carburized.'],
  'sy.suHizli': ['Hızlı soğuma perlit/beynit burnunu geçer.', 'The fast quench misses the pearlite/bainite nose.'],
  'sy.suYetersiz': ['Yüzeyde martenzit, çekirdekte ince perlit', 'Martensite at the surface, fine pearlite in the core'],
  'sy.suYetersiz.a': ['Sertleşebilirlik çok düşük; ancak ince kesitler tam sertleşir.', 'Very low hardenability; only thin sections harden through.'],
});

/* ------------------------------------------------------------------ */
/* Sabit noktalar (pin.js)                                             */
/* ------------------------------------------------------------------ */
sozlukEkle({
  'pin.sertlestirme': ['Sertleştirme', 'Hardening'],
  'pin.kesit': ['{ad} kesiti', '{ad} isopleth'],
  'pin.fark': ['Turuncu noktaya göre', 'vs. orange point'],
  'pin.kisayol': ['Tık: buraya git · Sağ tık: sil', 'Click: go here · Right-click: delete'],
  'pin.ekle': ['Sabitle', 'Pin'],
  'pin.ekle.ipucu': ['Turuncu noktayı sabitle (ya da Shift+tık)', 'Pin the orange point (or Shift+click)'],
  'pin.tekSil': ['Sabiti sil', 'Remove pin'],
  'pin.tekSil.ipucu': ['Sabit noktayı sil', 'Remove the pinned point'],
  'pin.menu': ['Sabitleri sil ({n})', 'Remove pins ({n})'],
  'pin.menu.ipucu': ['Hangi sabitin silineceğini seç', 'Choose which pin to remove'],
  'pin.hepsi': ['Hepsini sil', 'Remove all'],
  'ipucu': ['Tık/sürükle: nokta seç · Shift+tık: sabitle · Sağ tık: sabiti sil · Tekerlek: yakınlaştır',
    'Click/drag: pick a point · Shift+click: pin · Right-click: remove pin · Wheel: zoom'],
  // bilgi pencereleri ve kart düğmeleri (bilgi.js)
  'bilgi.hakkinda': ['{ad} hakkında bilgi', 'About: {ad}'],
  'katla': ['Katla / aç', 'Collapse / expand'],
});

/* ---------- HTML'deki sabit metinleri bağla ---------- */
function htmlDiliUygula(kok = document) {
  kok.querySelectorAll('[data-t]').forEach((e) => { e.textContent = t(e.dataset.t); });
  kok.querySelectorAll('[data-t-title]').forEach((e) => { e.title = t(e.dataset.tTitle); });
  kok.querySelectorAll('[data-t-aria]').forEach((e) => { e.setAttribute('aria-label', t(e.dataset.tAria)); });
  kok.querySelectorAll('[data-t-ph]').forEach((e) => { e.placeholder = t(e.dataset.tPh); });
}

/* ---------- dil değiştirme: durumu koru, sayfayı yeniden yükle ---------- */
const DURUM_ANAHTAR = 'fec-dil-durum';
function dilDegistir(yeni) {
  if (yeni === DIL) return;
  try {
    localStorage.setItem('fec-dil', yeni);
    if (typeof dilDurumuTopla === 'function') sessionStorage.setItem(DURUM_ANAHTAR, JSON.stringify(dilDurumuTopla()));
  } catch (e) { /* gizli pencere: durum korunmaz, dil yine değişir */ }
  // adres satırında ?lang= varsa onu da güncelle (yoksa eski dil geri gelirdi)
  const u = new URL(location.href);
  if (u.searchParams.has('lang')) u.searchParams.set('lang', yeni);
  location.replace(u.toString());
}
/** Önceki dilde kalan durumu bir kez oku */
function dilDurumuAl() {
  try {
    const s = sessionStorage.getItem(DURUM_ANAHTAR);
    sessionStorage.removeItem(DURUM_ANAHTAR);
    return s ? JSON.parse(s) : null;
  } catch (e) { return null; }
}
