'use strict';
/* Bilgi pencereleri: her kartın başlığındaki (i) düğmesi o kartın konusunu terim terim açıklar.
   Ayrıca kart başlıklarına katlama düğmesi ekler (katlı kartlar hatırlanır).
   İçerik eğitim amaçlıdır; sayısal örnekler bu uygulamanın kendi hesabından alınmıştır. */

const BILGI = {
  /* ------------------------------------------------------------------ */
  diyagram: {
    baslik: 'Diyagram nasıl okunur?',
    html: `
<p>Bu diyagram bir resim değil; her sınır, termodinamik dengenin bilgisayarla hesaplanmasından (CALPHAD) çizilir.
Yatay eksen <b>karbon oranı</b> (ağırlıkça %), dikey eksen <b>sıcaklık</b>tır. Diyagramdaki her nokta
"bu bileşimdeki çelik, bu sıcaklıkta yeterince uzun beklerse hangi fazlardan oluşur?" sorusunun cevabıdır.</p>
<h4>Renkler ve desenler</h4>
<ul>
  <li><b>Düz renk</b>: tek fazlı bölge (yalnızca östenit, yalnızca ferrit…).</li>
  <li><b>Çizgili</b>: iki ya da daha fazla fazın bir arada bulunduğu bölge; çizgilerin renkleri o fazlardır.</li>
  <li><b>Siyah noktalar</b>: değişmez noktalar (ötektoid, ötektik, peritektik).</li>
  <li><b>Turuncu kesikli çizgiler</b>: seçtiğin karbon (dikey) ve sıcaklık (yatay); kesiştikleri nokta seçili noktadır.</li>
  <li>İki fazlı bölgede seçili noktanın sağına ve soluna uzanan <b>kalın turuncu çizgi</b> bağlantı çizgisidir (tie-line): uçları iki fazın kendi karbon oranlarını gösterir.</li>
</ul>
<h4>Kullanım</h4>
<table>
  <tr><td>Tıkla / sürükle</td><td>Noktayı seç, sürükleyerek gez</td></tr>
  <tr><td><kbd>Shift</kbd> + tık</td><td>Noktayı sabitle (karşılaştırma için); üstüne gelince bilgi kartı açılır</td></tr>
  <tr><td>Sabit noktaya tık / sağ tık</td><td>Turuncu noktayı oraya taşı / sabiti sil</td></tr>
  <tr><td>Fare tekerleği</td><td>İmlecin olduğu yere yakınlaştır</td></tr>
  <tr><td><kbd>←</kbd> <kbd>→</kbd> <kbd>↑</kbd> <kbd>↓</kbd></td><td>Diyagram seçiliyken noktayı klavyeyle gezdir (<kbd>Shift</kbd> ile 10 kat hızlı)</td></tr>
  <tr><td>Görünüm düğmeleri</td><td>Sık bakılan bölgelere hızlı geçiş (çelik bölgesi, ötektoid köşesi…)</td></tr>
</table>
<h4>Metastabil diyagram</h4>
<p>Gösterilen Fe–Fe₃C (demir–sementit) diyagramıdır. Gerçekte en kararlı karbon fazı grafittir; fakat çeliklerde grafit
oluşumu çok yavaş olduğundan pratikte sementit oluşur. Bu yüzden hesapta grafit dışarıda bırakılır. Grafitli (kararlı)
diyagram gri ve sfero dökme demirlerin anlaşılmasında kullanılır.</p>
<div class="ozet">Diyagram <b>denge</b> durumunu gösterir. Hızlı soğumada oluşan martenzit, beynit gibi yapılar bu diyagramda yoktur;
onlar için "Soğuma ve sertleşme" kartına bak.</div>`,
  },

  /* ------------------------------------------------------------------ */
  kAlas: {
    baslik: 'Çelik ve alaşım elementleri',
    html: `
<p>Çeliğin davranışını karbonla birlikte alaşım elementleri belirler. Bu kart iki iş görür: kütüphaneden çelik seçmek
ve bileşimi elle girip kaydetmek.</p>
<h4>Kütüphane ve nominal bileşim</h4>
<p>Standartlar (EN, ISO, SAE) her element için bir <b>aralık</b> verir; ör. 42CrMo4'te C %0,38–0,45. Hesapta aralığın
ortası kullanılır. Standartta yalnızca üst sınır varsa ("Si ≤ 0,40") tipik bir değer alınır. Gerçek döküm analizi
aralığın herhangi bir yerinde olabilir; elindeki sertifikanın değerlerini girip kaydetmek en doğru sonucu verir.</p>
<h4>Gamajen ve alfajen elementler</h4>
<p><b>Gamajen</b> (östenit yapıcı: C, Mn, Ni, Cu, N) östenit (γ) alanını genişletir, A1 ve A3'ü düşürür.
<b>Alfajen</b> (ferrit yapıcı: Si, Cr, Mo, V, W, Ti, Nb) ferrit (α) alanını genişletir, A1'i yükseltir.
Hemen hemen bütün alaşım elementleri ötektoid noktayı daha düşük karbona kaydırır; bu yüzden alaşımlı bir çelik
%0,6 C'de bile ötektoid ya da hiperötektoid davranabilir.</p>
<h4>Elementlerin etkileri</h4>
<table>
  <tr><th>Element</th><th>Faz</th><th>Sertleşebilirlik</th><th>Karbür</th><th>Öne çıkan etki</th></tr>
  <tr><td><b>C</b></td><td>γ</td><td>artırır</td><td>Fe₃C</td><td>Martenzit sertliğini belirler; Ms'i en çok düşüren element</td></tr>
  <tr><td><b>Mn</b></td><td>γ</td><td>güçlü artırır</td><td>zayıf</td><td>Kükürtü MnS olarak bağlar; fazlası kalıntı östenit ve tane büyümesi eğilimi</td></tr>
  <tr><td><b>Si</b></td><td>α</td><td>orta</td><td>yapmaz</td><td>Deoksidan; ferriti sertleştirir; sementit oluşumunu geciktirir (yay çelikleri)</td></tr>
  <tr><td><b>Cr</b></td><td>α</td><td>güçlü artırır</td><td>M₇C₃, M₂₃C₆</td><td>Aşınma ve temper direnci; %12 üstünde paslanmazlık</td></tr>
  <tr><td><b>Ni</b></td><td>γ</td><td>orta</td><td>yapmaz</td><td>Tokluğu, özellikle düşük sıcaklık tokluğunu artırır</td></tr>
  <tr><td><b>Mo</b></td><td>α</td><td>çok güçlü</td><td>M₂C, M₆C</td><td>Temper gevrekliğini azaltır; sıcakta dayanım; az miktarda bile etkili</td></tr>
  <tr><td><b>V</b></td><td>α</td><td>çözünmüşse artırır</td><td>MC (VC)</td><td>Tane inceltir; çok kararlı karbür, ikincil sertleşme</td></tr>
  <tr><td><b>W</b></td><td>α</td><td>orta</td><td>M₆C</td><td>Sıcak sertlik (takım çelikleri)</td></tr>
  <tr><td><b>Cu</b></td><td>γ</td><td>hafif</td><td>yapmaz</td><td>Atmosferik korozyon direnci; fazlası sıcak şekillendirmede çatlama riski</td></tr>
</table>
<p class="not-satir">Karbür yapıcı elementler (Cr, Mo, V, W) karbonun bir kısmını karbür olarak bağlar. Östenitleme sıcaklığında çözünmeyen
karbürler hem tane büyümesini engeller hem de östenitteki karbonu (ve sertleşebilirliği) azaltır.</p>
<h4>Gerçek hesap ve empirik model</h4>
<p><b>Gerçek hesap</b> (CALPHAD kesiti) işaretliyse ve bu alaşım için hesap hazırsa (listede "● hesap"), diyagram o çeliğin
termodinamik kesitine geçer: karbürler ayrı fazlar olarak görünür. Hesap yoksa <b>empirik model</b> kullanılır: ikili
Fe–C sınırları, Andrews (1965) formüllerindeki alaşım katsayılarıyla kaydırılır.</p>
<h4>Kaydetme</h4>
<p>Elle girdiğin bileşimi bir adla kaydedebilirsin; kayıtlı çelikler arama listesinin en üstünde turuncu görünür ve bu
tarayıcıda saklanır. Kaydettiğin bileşim, hesabı hazır bir alaşımla aynıysa gerçek hesap otomatik açılır.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kIslem: {
    baslik: 'Isıl işlem sıcaklıkları',
    html: `
<p>Isıl işlem; çeliği belirli bir sıcaklığa ısıtmak, orada bekletmek ve belirli bir hızla soğutmaktır. Sıcaklık, faz
diyagramındaki kritik çizgilere göre seçilir; bu kart seçili karbon için bu aralıkları hesaplar ve diyagramda bant olarak çizer.</p>
<table>
  <tr><th>İşlem</th><th>Sıcaklık</th><th>Soğuma</th><th>Amaç / sonuç</th></tr>
  <tr><td><b>Tam tavlama</b></td><td>Hipo: A3 + 30–50 °C<br>Hiper: A1 + 30–50 °C</td><td>Fırında, çok yavaş</td><td>En yumuşak hal; kaba perlit. Talaşlı işlenebilirlik, iç gerilimin giderilmesi</td></tr>
  <tr><td><b>Normalizasyon</b></td><td>Hipo: A3 + 50–70 °C<br>Hiper: Acm + 50–70 °C</td><td>Durgun havada</td><td>Tane inceltme ve homojenleştirme; ince perlit. Döküm ve dövme sonrası standart işlem</td></tr>
  <tr><td><b>Sertleştirme</b></td><td>Hipo: A3 + 30–50 °C<br>Hiper: A1 + 30–50 °C</td><td>Su / yağ (hızlı)</td><td>Martenzit; en yüksek sertlik. Ardından mutlaka <b>temperleme</b></td></tr>
  <tr><td><b>Küreselleştirme</b></td><td>A1'in hemen altı (ya da A1 çevresinde salınım)</td><td>Yavaş</td><td>Sementit küreleşir; en iyi şekillendirilebilirlik, hiperötektoid çeliklerde sertleştirme öncesi hazırlık</td></tr>
  <tr><td><b>Gerilim giderme</b></td><td>550–650 °C (A1 altı)</td><td>Yavaş</td><td>Faz dönüşümü olmadan kaynak / talaş / soğuk şekillendirme gerilimlerini azaltma</td></tr>
</table>
<h4>Neden hipo ve hiper farklı?</h4>
<p><b>Hipoötektoid</b> çelikte (ötektoid karbondan az) A3 üstüne çıkılmazsa ferrit tamamen östenite dönüşmez; su verince bu ferrit yumuşak
noktalar olarak kalır. <b>Hiperötektoid</b> çelikte ise sertleştirme Acm'nin üstünde değil, <b>A1 + 30–50 °C</b>'de yapılır:</p>
<ul>
  <li>Acm üstünde bütün sementit çözünür, östenitin karbonu artar → Ms düşer, <b>kalıntı östenit</b> artar.</li>
  <li>Yüksek sıcaklıkta <b>tane irileşir</b>, su vermede <b>çatlama ve çarpılma</b> riski büyür.</li>
  <li>Çözünmeden kalan küçük sementit taneleri <b>aşınma direncine</b> katkı verir (ör. 100Cr6 rulman çeliği).</li>
</ul>
<h4>Neden "+30–50 °C"?</h4>
<p>Dönüşüm zaman ister, parçanın içi yüzeyden geç ısınır, fırın ve termokupl toleransları vardır. Fazlası ise tane büyümesi,
yüzeyde karbon kaybı (dekarbürizasyon) ve oksitlenme getirir. Bekleme süresi için yaygın atölye kuralı: <b>kesitin her 25 mm'si için
yaklaşık 1 saat</b> (malzemeye, fırına ve işleme göre değişir).</p>
<h4>Ae, Ac ve Ar</h4>
<p>Diyagramdaki çizgiler <b>denge</b> değerleridir (Ae). Isıtırken dönüşüm biraz daha yüksek sıcaklıkta (<b>Ac</b>, Fransızca <i>chauffage</i> = ısıtma),
soğuturken biraz daha düşük sıcaklıkta (<b>Ar</b>, <i>refroidissement</i> = soğuma) gerçekleşir. Fark ısıtma/soğutma hızıyla büyür.
Üretici veri sayfalarındaki değerler genelde Ac'dir ve birkaç ila birkaç on derece yüksektir.</p>
<h4>Gerçek hesapta bantlar</h4>
<p>Alaşımlı kesitte A1 tek çizgi değildir; Ae1 (östenit başlar) ile ferritin bittiği sıcaklık arasında üç fazlı bir banttır.
Bantlar bu gerçek sınırlardan çizilir. Karbür yapıcı elementli çeliklerde (Cr, Mo, V) karbürlerin yeterince çözünmesi için üretici
tabloları genellikle biraz daha yüksek sıcaklık önerir (ör. 42CrMo4 sertleştirme 820–860 °C). Kesin değer için çeliğin veri sayfası esastır.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kSogu: {
    baslik: 'Soğuma ve sertleşme',
    html: `
<p>Östenitleme sıcaklığından sonra östenitin neye dönüşeceğini <b>soğuma hızı</b> belirler. Faz diyagramı yalnızca çok yavaş (denge)
soğumayı anlatır; hızlı soğumada difüzyon yetişmez ve denge dışı yapılar oluşur.</p>
<table>
  <tr><th>Yapı</th><th>Oluştuğu durum</th><th>Özellik</th></tr>
  <tr><td><b>Kaba perlit</b></td><td>Fırında yavaş soğuma (~700 °C civarında dönüşüm)</td><td>Yumuşak, kolay işlenir</td></tr>
  <tr><td><b>İnce perlit</b></td><td>Havada soğuma (normalizasyon)</td><td>Daha mukavemetli ve tok</td></tr>
  <tr><td><b>Beynit</b></td><td>Orta hız / ~250–550 °C'de izotermal bekleme</td><td>Mukavemet ve tokluk dengesi</td></tr>
  <tr><td><b>Martenzit</b></td><td>Ms altına hızlı soğuma (su, yağ)</td><td>Çok sert ve gevrek; temperleme şart</td></tr>
</table>
<h4>Martenzit, Ms ve Mf</h4>
<p>Martenzit difüzyonsuz, kayma ile oluşan bir dönüşümdür: karbon ferrit kafesinde hapsolur ve kafesi çarpıtır, sertlik buradan gelir.
Dönüşüm <b>Ms</b>'de başlar ve sıcaklık düştükçe ilerler; <b>Mf</b>'de biter. Ms'i karbon ve alaşım elementleri düşürür. Burada Andrews'in
formülü kullanılır:</p>
<div class="formul">Ms (°C) = 539 − 423·C − 30,4·Mn − 17,7·Ni − 12,1·Cr − 7,5·Mo</div>
<h4>Kalıntı östenit</h4>
<p>Mf oda sıcaklığının altındaysa dönüşüm tamamlanamaz, bir kısım östenit dönüşmeden kalır. Oranı Koistinen–Marburger bağıntısıyla tahmin edilir:</p>
<div class="formul">martenzit oranı = 1 − exp[−0,011·(Ms − T)]</div>
<p>Kalıntı östenit boyut kararsızlığına ve sertlik kaybına yol açar; gerekiyorsa <b>sıfıraltı işlem</b> (−80 °C ve altı) ile dönüştürülür.
Yüksek karbonlu çeliklerde (ör. %1 C) belirgindir.</p>
<h4>Sertlik ve sertleşebilirlik farkı</h4>
<ul>
  <li><b>Sertlik</b>: tam martenzit ne kadar sert olur? Neredeyse yalnızca <b>karbona</b> bağlıdır (Hodge–Orehoski). ~%0,6 C üstünde
  kalıntı östenit nedeniyle pek artmaz (~64–66 HRC).</li>
  <li><b>Sertleşebilirlik</b>: martenzit ne kadar <b>derine</b> kadar oluşur? Alaşım elementleri belirler. Ölçüsü <b>ideal kritik çap D<sub>I</sub></b>'dir:
  sonsuz hızla soğutulduğunda merkezinde %50 martenzit oluşan çubuğun çapı. Burada ASTM A255 çarpanlarıyla hesaplanır. Pratikte
  Jominy uçtan su verme deneyiyle ölçülür.</li>
</ul>
<h4>Soğutma ortamının şiddeti</h4>
<p>Grossmann H değeri (yaklaşık): durgun hava ~0,02 · durgun yağ ~0,3 · karıştırılan yağ ~0,5–0,8 · durgun su ~1 · karıştırılan su ~1,5–2 · tuzlu su ~2–5.
Ortam ne kadar şiddetliyse o kadar kalın kesit sertleşir; ama çatlama ve çarpılma riski de o kadar artar. Bu yüzden yüksek
sertleşebilirlikli alaşımlı çelikler yağda, sade karbonlu çelikler suda sertleştirilir.</p>
<div class="ozet">Karttaki yapı tahmini ~25 mm kesit için kaba bir yönlendirmedir. Kesin sonuç parça kalınlığına ve çeliğin CCT (sürekli
soğuma dönüşüm) diyagramına bağlıdır.</div>`,
  },

  /* ------------------------------------------------------------------ */
  kBolge: {
    baslik: 'Seçilen nokta: fazlar ve bölgeler',
    html: `
<p><b>Faz</b>, malzemenin kimyasal bileşimi ve kristal yapısı her yerde aynı olan, sınırlarla ayrılmış bölümüdür. Bu kart seçili
noktada hangi fazların bir arada bulunduğunu söyler.</p>
<h4>Fe–C sistemindeki fazlar</h4>
<table>
  <tr><th>Faz</th><th>Kristal</th><th>En fazla C</th><th>Not</th></tr>
  <tr><td><b>α-ferrit</b></td><td>HMK (BCC)</td><td>~%0,02 (727 °C'de)</td><td>Yumuşak, sünek, 770 °C altında manyetik</td></tr>
  <tr><td><b>γ-östenit</b></td><td>YMK (FCC)</td><td>~%2,1 (1148 °C'de)</td><td>Isıl işlemin başlangıç fazı; manyetik değil</td></tr>
  <tr><td><b>δ-ferrit</b></td><td>HMK (BCC)</td><td>~%0,09</td><td>Yalnızca çok yüksek sıcaklıkta; döküm ve kaynakta önemli</td></tr>
  <tr><td><b>Sementit Fe₃C</b></td><td>ortorombik</td><td>%6,69 (sabit)</td><td>Çok sert ve gevrek bir karbür</td></tr>
  <tr><td><b>Sıvı (L)</b></td><td>—</td><td>—</td><td>Ergiyik</td></tr>
</table>
<p class="not-satir">Bu uygulamanın hesabı ders kitabı değerlerinden biraz farklı sayılar verebilir (ör. östenitin en fazla C'si %2,05, ötektik %4,38).
Kitaplardaki %2,14 ve %4,3 eski deneysel derlemelerdir; hesap güncel termodinamik veritabanına dayanır.</p>
<h4>Gibbs faz kuralı</h4>
<p>Sabit basınçta <b>F = B − P + 1</b> (F: serbestlik derecesi, B: bileşen sayısı, P: faz sayısı). İkili Fe–C'de (B = 2):</p>
<ul>
  <li><b>Tek fazlı bölge</b> (F = 2): sıcaklık ve bileşim bağımsız değiştirilebilir.</li>
  <li><b>İki fazlı bölge</b> (F = 1): sıcaklığı seçince iki fazın bileşimleri kendiliğinden belirlenir (bağlantı çizgisinin uçları).</li>
  <li><b>Üç faz</b> (F = 0): yalnızca tek bir sıcaklıkta mümkündür; ötektoid, ötektik ve peritektik çizgileri budur.</li>
</ul>
<h4>Alaşımlı kesitte</h4>
<p>Alaşımlı çelikte bileşen sayısı arttığı için faz kuralı daha fazla fazın bir arada bulunmasına izin verir. Bu yüzden kesitte
<b>üç ve dört fazlı bölgeler</b> (ör. γ + α + M₂₃C₆) geniş alanlar kaplar ve A1 tek çizgi değil, bir bant olur. Alaşım karbürleri
(M₇C₃, M₂₃C₆, M₆C, MC) ayrı fazlar olarak görünür; M, metal atomlarının (Fe, Cr, Mo, V…) karışımı demektir.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kOran: {
    baslik: 'Faz oranları ve kaldıraç kuralı',
    html: `
<p>İki fazlı bir bölgede hem <b>hangi fazların</b> hem de <b>ne kadar</b> bulunduklarını bilmek gerekir. Bu kart her fazın
ağırlıkça oranını ve o fazın kendi karbon oranını verir.</p>
<h4>Kaldıraç kuralı</h4>
<p>Seçili sıcaklıkta yatay bir çizgi (bağlantı çizgisi) çekilir; iki fazlı bölgenin sınırlarını kestiği noktalar fazların kendi
bileşimleridir: <b>C<sub>α</sub></b> (sol) ve <b>C<sub>β</sub></b> (sağ). Karbon kütlesinin korunumundan:</p>
<div class="formul">W<sub>α</sub> = (C<sub>β</sub> − C₀) / (C<sub>β</sub> − C<sub>α</sub>)  ·  W<sub>β</sub> = (C₀ − C<sub>α</sub>) / (C<sub>β</sub> − C<sub>α</sub>)</div>
<p>C₀ çeliğin karbonudur. Kural adını tahterevalliden alır: bir faz, çeliğin bileşimine ne kadar <b>uzaksa</b> o kadar <b>az</b>dır.</p>
<p><b>Örnek</b> (bu uygulamanın hesabı): %0,30 C'li çelik 780 °C'de α + γ bölgesindedir. Bu sıcaklıkta ferritin karbonu %0,014,
östenitin karbonu %0,435'tir. Ferrit oranı = (0,435 − 0,30) / (0,435 − 0,014) ≈ <b>%32</b>, östenit ≈ <b>%68</b>.</p>
<h4>Ağırlıkça mı, hacimce mi?</h4>
<p>Hesap ağırlıkça yapılır. Metalografide ise görüntüdeki alan (≈ hacim) oranı ölçülür. Ferrit ve sementit yoğunlukları yakın olduğu için
(7,87 ve ~7,7 g/cm³) çeliklerde fark küçüktür.</p>
<h4>Alaşımlı kesitte</h4>
<p>Çok bileşenli bir çelikte bağlantı çizgileri kesitin düzleminde durmaz (fazlar karbonla birlikte alaşım elementlerini de farklı oranlarda
paylaşır). Bu yüzden kesit diyagramından kaldıraç kuralı <b>uygulanamaz</b>; oranlar doğrudan termodinamik hesaptan alınır ve kartta
"hesap" diye belirtilir.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kKritik: {
    baslik: 'Kritik sıcaklıklar ve dönüşümler',
    html: `
<p>Seçili karbon oranındaki çelik ısıtılırken faz değişimlerinin olduğu sıcaklıklar <b>kritik sıcaklıklardır</b>. Isıl işlem sıcaklıkları
bunlara göre seçilir.</p>
<table>
  <tr><th>Ad</th><th>Anlamı</th></tr>
  <tr><td><b>A1</b></td><td>Ötektoid sıcaklığı (~727 °C). Altında ferrit + sementit, üstünde östenit oluşmaya başlar.</td></tr>
  <tr><td><b>A3</b></td><td>Hipoötektoid çelikte ferritin tamamen östenite döndüğü sıcaklık. Karbon arttıkça düşer.</td></tr>
  <tr><td><b>Acm</b></td><td>Hiperötektoid çelikte sementitin östenitte tamamen çözündüğü sıcaklık. Karbon arttıkça hızla yükselir.</td></tr>
  <tr><td><b>A2</b></td><td>Curie sıcaklığı (~770 °C): ferrit manyetikliğini kaybeder; faz dönüşümü değildir, bu yüzden diyagramda çizgi olarak yoktur.</td></tr>
  <tr><td><b>Solidus / likidus</b></td><td>Ergimenin başladığı / bittiği sıcaklık. Döküm sıcaklığı likidüsün üzerinde seçilir.</td></tr>
</table>
<h4>Değişmez dönüşümler</h4>
<ul>
  <li><b>Ötektoid</b> (~727 °C, ~%0,76 C): γ → α + Fe₃C. Ürünü <b>perlit</b>tir (ince ferrit ve sementit lamelleri).</li>
  <li><b>Ötektik</b> (~1148 °C, ~%4,3 C): L → γ + Fe₃C. Ürünü <b>ledeburit</b>tir; beyaz dökme demirin yapısıdır.</li>
  <li><b>Peritektik</b> (~1495 °C, ~%0,17 C): δ + L → γ. Düşük karbonlu çeliklerin katılaşmasında ve kaynakta önemlidir.</li>
</ul>
<h4>Ac, Ae, Ar</h4>
<p>Değerler dengedir (Ae). Gerçek ısıtmada dönüşüm biraz daha yüksekte (Ac), soğutmada biraz daha düşükte (Ar) olur.
Ayrıntı için "Isıl işlem sıcaklıkları" bilgi penceresine bak.</p>
<h4>Alaşımlı kesitte: Ae1, Ae3, Aecm</h4>
<p>Alaşımlı çelikte ötektoid dönüşüm bir sıcaklık <b>aralığında</b> olur. <b>Ae1</b>: östenitin ilk oluştuğu sıcaklık. <b>Ae3</b>: ferritin bittiği
sıcaklık (hiperötektoidde "A1 bandının üstü"). <b>Aecm</b>: son karbürün çözündüğü sıcaklık. Listede ayrıca hangi karbürün hangi sıcaklıkta
çözündüğü ya da başka bir karbüre dönüştüğü görünür. Çok kararlı MC karbürleri (VC gibi) çok yüksek sıcaklığa kadar kalabilir;
bunlar tane inceltici olarak bilerek çözünmeden bırakıldığı için Aecm'ye katılmaz.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kYatay: {
    baslik: 'İzoterm: bir sıcaklıktaki sınırlar',
    html: `
<p>Seçili sıcaklıkta diyagramı soldan sağa kesen yatay çizgiye <b>izoterm</b> denir. Bu kart o çizgi boyunca hangi karbon aralığında
hangi bölgenin olduğunu listeler; seçili noktanın bölgesi vurgulanır.</p>
<h4>Ne işe yarar?</h4>
<ul>
  <li>Belirli bir fırın sıcaklığında <b>östenitin çözebileceği en fazla karbonu</b> okursun (östenit bölgesinin sağ sınırı = Acm eğrisi).
  Sementasyonda yüzey karbonunun üst sınırı ve hiperötektoid çelikte çözünmeden kalacak karbür miktarı buradan anlaşılır.</li>
  <li>İki fazlı bir bölgenin uçları o sıcaklıkta iki fazın <b>kendi karbon oranlarıdır</b>; kaldıraç kuralı bu iki sayıyla hesaplanır.</li>
  <li>Farklı karbonlu çeliklerin aynı fırında aynı sıcaklıkta nasıl davranacağını tek bakışta karşılaştırırsın.</li>
</ul>
<h4>Alaşımlı kesitte</h4>
<p>Kesitte bölge sınırları fazların kendi karbonu <b>değildir</b>; yalnızca o çeliğin (o alaşım oranlarıyla) hangi karbonda hangi faz
kümesine sahip olduğunu gösterir.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kYapi: {
    baslik: 'Yavaş soğuma sonrası mikroyapı',
    html: `
<p>Çelik östenit bölgesinden yavaşça (denge koşullarına yakın) soğutulduğunda oda sıcaklığındaki mikroyapıyı tahmin eder.
Oranlar kaldıraç kuralıyla, A1'in hemen altında hesaplanır.</p>
<h4>Bileşenler</h4>
<ul>
  <li><b>Proötektoid ferrit</b>: hipoötektoid çelikte A3 ile A1 arasında, ötektoidden <i>önce</i> oluşan ferrit; tane sınırlarında açık renkli taneler.</li>
  <li><b>Proötektoid (ikincil) sementit</b>: hiperötektoid çelikte Acm ile A1 arasında tane sınırlarında oluşan sementit ağı. Gevreklik yapar;
  küreselleştirme ile giderilir.</li>
  <li><b>Perlit</b>: A1'de kalan östenitin ötektoid dönüşümüyle oluşan lamelli α + Fe₃C. Kendi içinde yaklaşık <b>%89 ferrit, %11 sementit</b>tir.</li>
  <li><b>Ledeburit</b> (dökme demir): ötektik dönüşüm ürünü; soğumada içindeki östenit de perlite döner ("dönüşmüş ledeburit").</li>
</ul>
<h4>Metalografide karbon tahmini</h4>
<p>Tersinden de kullanılır: yavaş soğumuş hipoötektoid bir çeliğin mikroyapısındaki perlit oranı ölçülürse karbon yaklaşık olarak
<b>%C ≈ perlit oranı × 0,76</b> ile bulunur (ör. yarısı perlit ise ≈ %0,38 C). Bu, kalitesi bilinmeyen bir parçanın hızlı tanınmasında kullanılan
pratik bir yöntemdir.</p>
<h4>Alaşımlı kesitte</h4>
<p>Kart, A1 bandının biraz altındaki denge fazlarını gösterir: ferrit, sementit ve alaşım karbürleri. Hangi karbürün gerçekten oluşacağı soğuma
hızına ve süreye bağlıdır; denge hesabı bir üst sınır ve yön verir.</p>`,
  },

  /* ------------------------------------------------------------------ */
  yontem: {
    baslik: 'Yöntem ve kaynaklar',
    html: `
<h4>İkili Fe–C diyagramı</h4>
<p>Sınırlar <b>pycalphad</b> (açık kaynak CALPHAD kütüphanesi) ile Gibbs enerjisi minimizasyonundan hesaplanır. Veritabanı:
<b>Fei &amp; Brosh (2014)</b> Fe–C değerlendirmesi (<code>cfe_broshe.tdb</code>). Fazlar: BCC_A2, FCC_A1, CEMENTITE, LIQUID; grafit dışarıda
bırakılarak metastabil Fe–Fe₃C diyagramı elde edilir. 400–1600 °C arası 1 °C adımla taranır; iki fazlı bölge sınırları bağlantı
çizgisi uçlarından alınır, değişmez noktalar 0,01 °C hassasiyetle bulunur.</p>
<h4>Alaşımlı çelik kesitleri (gerçek hesap)</h4>
<p><b>MatCalc açık çelik veritabanı</b> mc_fe v2.062 (TU Wien, Open Database License) pycalphad ile kullanılır. Her çelik için alaşım
elementleri sabit tutularak karbon 0–%1,8, sıcaklık 550–1100 °C aralığında dikey kesit (izoplet) hesaplanır. Faz oranları ağırlıkça,
fazların karbonu doğrudan hesaptandır. Doğrulama: C45, 42CrMo4, 16MnCr5, 100Cr6 için Ae1/Ae3/Aecm değerleri literatürdeki ölçülen
Ac değerleriyle uyumludur.</p>
<h4>Empirik bağıntılar</h4>
<ul>
  <li>Alaşımın A1/A3'e etkisi: K. W. Andrews, <i>J. Iron Steel Inst.</i> 203 (1965) — alaşım katsayıları hesaplanan ikili eğrilere eklenir.</li>
  <li>Ötektoid karbonun kayması: Bain diyagramından okunan yaklaşık eğimler.</li>
  <li>Ms: Andrews (1965) doğrusal bağıntısı. Kalıntı östenit: Koistinen &amp; Marburger (1959).</li>
  <li>Tam martenzit sertliği: Hodge &amp; Orehoski (1946). Sertleşebilirlik: ASTM A255 (Grossmann D<sub>I</sub>), tane boyutu 7.</li>
</ul>
<h4>Çelik kütüphanesi</h4>
<p>63 düşük alaşımlı çelik; bileşim aralıkları EN ISO 683-1/-2/-3/-17, EN 10025-2, EN 10083, EN 10085, EN 10089, EN 10132, ISO 4957,
EN 10213 ve EN 10293 standartlarından, nominal değer aralık ortasıdır. P, S, B, Al, N, Nb, Ti modelde yoktur.</p>
<h4>Sınırlar</h4>
<ul>
  <li>Bütün diyagram değerleri <b>denge</b> değerleridir; gerçek ısıtma/soğutmada hıza bağlı sapma olur.</li>
  <li>Paslanmaz ve yüksek alaşımlı takım çelikleri (sigma, Laves fazları) kapsam dışındadır.</li>
  <li>Soğuma yapısı tahminleri kabadır; kesin sonuç için çeliğin CCT diyagramı ve üretici veri sayfası esastır.</li>
</ul>
<h4>Atıflar</h4>
<ul>
  <li>pycalphad — R. Otis &amp; Z.-K. Liu, <i>J. Open Res. Softw.</i> 5 (2017) 1 (MIT lisansı).</li>
  <li>Fe–C değerlendirmesi — Fei &amp; Brosh (2014), <code>cfe_broshe.tdb</code>.</li>
  <li>Alaşımlı çelik kesitleri, E. Povoden-Karadeniz ve A. Jacob'un (TU Wien) MatCalc mc_fe v2.062 veritabanından üretilmiştir;
  bu veritabanı <b>Open Database License (ODbL)</b> ile yayımlanmıştır.</li>
</ul>
<div class="ozet">Faz Atlası eğitim ve ön tasarım içindir. Üretimde kullanılacak sıcaklıklar malzeme sertifikası ve üretici verisiyle doğrulanmalıdır.</div>
<p class="not-satir">Faz Atlası v1.0 · 63 çelik, 52 hesaplanmış kesit · açık kaynak</p>`,
  },
};

/* ---------- pencere ---------- */
const bilgiPencere = document.getElementById('bilgiPencere');
function bilgiAc(anahtar) {
  const b = (DIL === 'en' ? BILGI_EN : BILGI)[anahtar];
  if (!b) return;
  document.getElementById('bpBaslik').textContent = b.baslik;
  const govde = document.getElementById('bpGovde');
  govde.innerHTML = b.html;
  govde.scrollTop = 0;
  // <dialog> desteklemeyen eski tarayıcılarda da açılsın
  if (!bilgiPencere.open) { if (bilgiPencere.showModal) bilgiPencere.showModal(); else bilgiPencere.setAttribute('open', ''); }
}
const bilgiKapat = () => { if (bilgiPencere.close) bilgiPencere.close(); else bilgiPencere.removeAttribute('open'); };
document.getElementById('bpKapat').addEventListener('click', bilgiKapat);
// pencerenin dışına (arka plana) tıklayınca kapansın
bilgiPencere.addEventListener('click', (e) => {
  const r = bilgiPencere.getBoundingClientRect();
  if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) bilgiKapat();
});
document.addEventListener('click', (e) => {
  const b = e.target.closest('[data-bilgi]');
  if (b) { e.preventDefault(); bilgiAc(b.dataset.bilgi); }
});

/* ---------- kart başlıklarına (i) ve katlama düğmesi ---------- */
const KATLI_ANAHTAR = 'fec-katli-kartlar-v1';
const katli = new Set((() => { try { const l = JSON.parse(localStorage.getItem(KATLI_ANAHTAR)); return Array.isArray(l) ? l : []; } catch (e) { return []; } })());
function katliKaydet() { try { localStorage.setItem(KATLI_ANAHTAR, JSON.stringify([...katli])); } catch (e) { /* gizli pencere */ } }

const KATLA_SVG = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6l4 4 4-4"/></svg>';
function kartBasliklariniDonat() {
  document.querySelectorAll('#panel > .kart').forEach((kart) => {
    const bas = kart.querySelector(':scope > .kart-bas');
    kart.classList.toggle('kapali', katli.has(kart.id));
    if (!bas || bas.querySelector('.bilgi-btn')) return;
    const ad = bas.querySelector('h3') ? bas.querySelector('h3').textContent : '';
    if (BILGI[kart.id]) {
      bas.insertAdjacentHTML('beforeend',
        `<button class="bilgi-btn" data-bilgi="${kart.id}" title="${t('bilgi.hakkinda', { ad })}" aria-label="${t('bilgi.hakkinda', { ad })}">i</button>`);
    }
    bas.insertAdjacentHTML('beforeend',
      `<button class="katla-btn" data-katla="${kart.id}" title="${t('katla')}" aria-expanded="${!katli.has(kart.id)}">${KATLA_SVG}</button>`);
  });
}
document.getElementById('panel').addEventListener('click', (e) => {
  const b = e.target.closest('[data-katla]');
  if (!b) return;
  const id = b.dataset.katla;
  if (katli.has(id)) katli.delete(id); else katli.add(id);
  katliKaydet();
  const kart = document.getElementById(id);
  kart.classList.toggle('kapali', katli.has(id));
  b.setAttribute('aria-expanded', !katli.has(id));
});
KANCA.panel.push(kartBasliklariniDonat);
kartBasliklariniDonat();
