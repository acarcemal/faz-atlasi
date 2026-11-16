# FAZ ATLASI 2.0: PRODUCTION-READY MİMARİ VE DÖNÜŞÜM DOKÜMANI
**Tarih:** 2026-11-02  
**Hazırlayan:** Antigravity (Cemal Acar için Teknik Danışmanlık ve Mimari Devir Raporu)  
**Hedef:** Claude Code / Claude Opus ile Sıfırdan Production-Ready Mimarinin Kurulması

---

## 1. YÖNETİCİ ÖZETİ VE VİZYON

Mevcut proje ("Faz Atlası v1"), GitHub Pages üzerinde çalışan, ikili Fe-C ve 63 düşük alaşımlı çeliğin dikey kesitlerini (izoplet) önceden hesaplanmış statik JavaScript dosyaları üzerinden gösteren başarılı bir **akademik prototip**tir.

Ancak proje iki büyük darboğazla karşılaşmıştır:
1. **Veri ve Çeşitlilik Darboğazı:** 63 çelik ve 8 element sanayi ve geniş kapsamlı kullanım için yetersizdir. Ancak 10.000 çeliğin kaba kuvvetle (brute-force) hesaplanması aylar sürecek bir hesaplama yükü olarak görülmektedir.
2. **Yazılım Mimarisi Darboğazı:** Verilerin `.js` dosyalarında saklanması (`window.CELIK_KUTUPHANE`), veritabanı (PostgreSQL/SQLite) olmaması, global değişken kirliliği ve build pipeline eksikliği yazılımı production-ready olmaktan uzaklaştırmaktadır.

**Hedeflenen Faz Atlası v2.0:**
* **Client-Server (İstemci-Sunucu)** mimarisine geçiş.
* İstemci (Frontend): En düşük donanımlı atölye PC'sinde ve cep telefonunda bile yağ gibi akan ultra hafif, tip güvenli (TypeScript) arayüz.
* Sunucu (Backend): FastAPI + `pycalphad` (C++/LLVM motoru) + `mc_fe_pycalphad.tdb` veritabanı.
* Veritabanı: 10.000+ çeliğin kimyasal aralıklarını tutan ilişkisel veritabanı (PostgreSQL / SQLite).
* Hesaplama Optimizasyonu: **Alaşım Kümeleme (Alloy Clustering)**, **Sınır İzleme (Boundary Tracing)** ve **İsteğe Bağlı Tek Nokta Hesabı (On-Demand Equilibrium)** ile hesap yükünün aylar yerine saatlere indirilmesi.

---

## 2. METALURJİK VE TERMODİNAMİK ÇÖZÜMLER

### 2.1. "10.000 Çelik" Yanılsaması ve Alaşım Kümeleme (Alloy Clustering)
* Bu projede **Karbon zaten X eksenidir.**
* C10'dan C60'a kadar tüm karbon çelikleri, St37, St52, 1010-1090 çelikleri **aynı dikey kesiti (saf karbon bazı)** paylaşır.
* 4130, 4140, 4150 (25CrMo4, 42CrMo4, 50CrMo4) çelikleri **aynı Cr-Mo dikey kesitini** paylaşır.
* Dünyadaki 10.000 ticari çeliğin %85'i aslında sadece **250–300 ana alaşım ailesine** aittir.
* **Yazılım Kuralı:** Veritabanında 10.000 çelik kaydı bulunur; ancak her çelik bir `alloy_family_id` ile eşleştirilir. Hesaplanacak kesit sayısı 10.000 değil, sadece ~300'dür!

### 2.2. Sınır İzleme (Boundary Tracing) ile 50 Kat Hızlanma
* **Mevcut Durum (Tam Izgara):** 111 sıcaklık × 65 karbon = 7.200 noktada Gibbs minimizasyonu. Çelik başına 5–10 dakika.
* **Yeni Durum (Sınır İzleme):** Fazların sıfır olduğu hatlar (solvus, solidus, liquidus, karbür çözünme çizgileri) kök bulma / bisection ile izlenir. Satır başına 65 nokta yerine sadece sınır noktaları (~3-4 nokta) taranır.
* **Sonuç:** Bir kesitin hesaplanması 5 dakikadan **10–15 saniyeye** düşer. 300 alaşım ailesi toplam **1–2 saat içinde** tamamen hesaplanır.

### 2.3. İsteğe Bağlı (On-Demand) Tek Nokta Denge Hesabı
* Sınırları çizilmiş diyagramda kullanıcı rastgele bir ($T, %C$) noktasına tıkladığında veya *"Bu noktadaki faz oranlarını hesapla"* butonuna bastığında:
* Sunucuya tek bir istek gider: `POST /api/equilibrium { bilesim, T }`
* `pycalphad` tek bir nokta için dengeyi **0.02 saniyede (20 milisaniye)** çözer!
* Dönen sonuç anında UI'da gösterilir: `{%64 Östenit, %36 Ferrit, faz bileşimleri}`.
* Bu sonuç sunucu önbelleğine (Cache) atılır.

### 2.4. Paslanmaz Çeliklerin Doğru Entegrasyonu
* **Martenzitik Paslanmazlar (1.4021 / AISI 420, 1.4034, 440B):** Fe-Cr-C sisteminde A1 bandı, $M_{23}C_6$ karbür çözünmesi ve Ms sıcaklığı normal şekilde hesaplanır ve gösterilir.
* **Östenitik Paslanmazlar (AISI 304 / 1.4301, 316 / 1.4401):**
  * Bu çeliklerde ferrit-östenit dönüşümü (A1/A3) yoktur.
  * MatCalc TDB veritabanı Fe-Cr-Ni için optimize edilmiştir; diyagramda stabil östenit (FCC_A1) alanı ve $M_{23}C_6$ çökmesi çıkar.
  * Arayüzde "Sertleştirme / Islah (Su verme)" kartı gizlenir; yerine **"Çözeltiye Alma Tavı (1050–1100 °C)"** ve 500–800 °C aralığı için **"Hassaslaşma (Sensitization) / Taneler Arası Korozyon Riski"** paneli açılır.
  * Ms değeri için "Oda sıcaklığının çok altında (<-100 °C) / Dönüşüm yok" gösterilir.

---

## 3. VERİTABANI VE VERİ TEDARİK STRATEJİSİ

### 3.1. Veri Kaynakları ve İndirilen Hazır Veriler
Projeye doğrudan aktarılmak üzere indirilen hazır veri setleri `hesap/veri_kaynaklari/` dizinine yerleştirilmiştir:
1. **`hesap/veri_kaynaklari/database_classification.csv`:** Çeliklerin ticari adları, kimyasal analizleri ve mikroyapı sınıfları (Mendeley Data DOI: 10.17632/mfhvdv4b8z.1).
2. **`hesap/veri_kaynaklari/steel_database_3234.xlsx`:** 3.234 çeliğin ayrıştırılmış tam kimyasal analizleri ve mekanik özellikleri (Mendeley Data DOI: 10.17632/jmwb9ddd43.1).
3. **Endüstriyel Standartlar & Web Scraping:** `steelnumber.com` üzerinden DIN / EN / AISI / JIS çapraz eşleştirmeleri.
4. **Kataloglar:** Asil Çelik ve Böhler/Uddeholm teknik el kitapları.

### 3.2. Veritabanı Şeması (PostgreSQL / SQLite)

```sql
-- 1. Alaşım Aileleri (Hesaplanan Dikey Kesitler)
CREATE TABLE alloy_families (
    id VARCHAR(64) PRIMARY KEY, -- Örn: 'Cr1.05_Mo0.22' veya 'saf'
    base_elements JSONB NOT NULL, -- {"Cr": 1.05, "Mo": 0.22}
    isopleth_boundaries JSONB, -- Poligon ve sınır eğrisi koordinatları
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Standart Çelikler Tablosu (TEK ÇELİK - ÇOKLU NORM KURALI)
-- DİKKAT: DIN, EN, AISI ve JIS karşılıkları olan aynı çelik ASLA ayrı ayrı mükerrer kaydedilmez!
-- Tek bir ana ID altında toplanır; kullanıcı AISI de aratsa, DIN de aratsa aynı çeliğe ulaşır.
CREATE TABLE steels (
    id SERIAL PRIMARY KEY,
    standard_name VARCHAR(64) NOT NULL, -- Örn: '42CrMo4' (EN standart adı)
    material_number VARCHAR(32),        -- Örn: '1.7225' (Alman Werkstoffnummer / DIN)
    aisi_sae VARCHAR(32),               -- Örn: '4140' (Amerikan AISI/SAE)
    jis VARCHAR(32),                    -- Örn: 'SCM440' (Japon JIS)
    group_name VARCHAR(64) NOT NULL,    -- Örn: 'Islah çeliği', 'Östenitik paslanmaz'
    standard_code VARCHAR(64),          -- Örn: 'EN ISO 683-2'
    usage_tr TEXT,
    usage_en TEXT,
    alloy_family_id VARCHAR(64) REFERENCES alloy_families(id)
);

-- 3. Kimyasal Aralıklar ve Nominal Değerler
CREATE TABLE steel_compositions (
    steel_id INT REFERENCES steels(id) ON DELETE CASCADE,
    element VARCHAR(4) NOT NULL,
    min_val DOUBLE PRECISION DEFAULT 0.0,
    max_val DOUBLE PRECISION NOT NULL,
    nominal_val DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (steel_id, element)
);

-- 4. Anlık Hesaplama Önbelleği (Calculation Cache)
CREATE TABLE calculation_cache (
    cache_key VARCHAR(64) PRIMARY KEY, -- SHA256(bilesim_json + T + P)
    result_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. YAZILIM MİMARİSİ VE TEKNOLOJİ YIĞINI

### 4.1. Backend (FastAPI + Python + pycalphad)
* **Framework:** FastAPI (Asenkron, hafif, otomatik OpenAPI/Swagger dokümantasyonu).
* **CALPHAD Motoru:** `pycalphad` 0.11.2, SymEngine (C++ türev motoru), NumPy/SciPy.
* **Veritabanı Dosyaları:** `hesap/tdb/mc_fe_pycalphad.tdb` ve `cfe_broshe.tdb`.
* **Performans / Warm Cache:** Faz modelleri (`prf` ve `models`) sunucu ayağa kalktığında bellekte başlatılır; her istekte baştan derlenmez (`hazir()` fonksiyonu global singleton yapılır).

#### Kritik API Endpoint'leri:
1. `GET /api/v1/steels`: Arama, filtreleme, sayfalama destekli çelik listesi.
2. `GET /api/v1/steels/{id}`: Çeliğin detayları, kimyasal bileşimi, nominal değerleri ve ısıl işlem rejimleri.
3. `GET /api/v1/isopleth/{family_id}`: Sadece sınır çizgilerini ve faz bölgelerini içeren hafif poligon JSON'ı.
4. `POST /api/v1/equilibrium/point`: Belirli bir sıcaklık ve bileşim için tek nokta termodinamik denge hesabı (20 ms).
   * Request: `{ "composition": {"C": 0.42, "Cr": 1.05, "Mo": 0.22}, "T": 760 }`
   * Response: `{ "phases": {"FCC_A1": 0.64, "BCC_A2": 0.36}, "carbon_in_phases": {"FCC_A1": 0.51, "BCC_A2": 0.02} }`

### 4.2. Frontend (TypeScript + Vite)
* **Teknoloji:** Modern TypeScript + Vite (Vanilla TS veya hafif Svelte/React).
* **Çizim Motoru:** SVG veya Canvas tabanlı faz diyagramı çizicisi.
* **Özellikler:**
  * Sadece sınır vektörlerini çizer; CPU ve RAM tüketimi sıfıra yakındır.
  * Tıklanan noktayı yakalar; tek nokta isteğini REST API'ye atıp gelen faz oranlarını anında panellere yansıtır.
  * Responsive (Masaüstü, tablet, mobil tam uyumlu).

### 4.3. Konteynerizasyon (Docker)
* `Dockerfile` ve `docker-compose.yml` ile PostgreSQL + FastAPI backend tek komutla (`docker compose up --build`) ayağa kalkar.

---

## 5. CLAUDE İÇİN AŞAMALI GELİŞTİRME PLANI (ACTION PLAN)

Claude Code / Claude Opus bu dönüşümü şu fazlarla adım adım hayata geçirecektir:

### Faz 1: Veritabanı ve Çelik Kütüphanesi Dönüşümü
1. `hesap/celik_kutuphanesi.py` içindeki 63 çeliği ve ek açık veri setlerini (Mendeley/Zenodo) içerecek SQLite/PostgreSQL veritabanı şemasını kurmak.
2. Alaşım ailelerini (Alloy Families) otomatik gruplayan migration script'ini yazmak.
3. Martenzitik ve östenitik paslanmaz çelikleri (1.4021, 1.4034, 304, 316) veritabanına eklemek.

### Faz 2: FastAPI Backend Çekirdeğinin Kurulması
1. `backend/` dizini altında FastAPI iskeletini oluşturmak.
2. `pycalphad` singleton yöneticisini yazmak (TDB modellerini bellekte sıcak tutan servis).
3. Tek nokta denge hesabı yapan `equilibrium/point` endpoint'ini yazmak ve 50 ms altı performansı doğrulamak.
4. Sınır izleme (boundary tracing) algoritmasını yazarak sadece sınır koordinatlarını üreten servisi kurmak.

### Faz 3: Östenitik Çelikler İçin Özel Isıl İşlem Mantığı
1. Backend'de çelik tipine göre ısıl işlem rejimini belirleyen servis katmanı yazmak.
2. Östenitik çeliklerde A1/A3 aramasını devre dışı bırakıp, çözeltiye alma tavı (1050–1100 °C) ve hassaslaşma risk aralığını (500–800 °C) döndürmek.

### Faz 4: Frontend Modernizasyonu ve API Entegrasyonu
1. `web/` tarafındaki statik JS dosyalarına olan bağımlılığı kaldırıp FastAPI REST API'sine bağlamak.
2. Tıklanan noktada "Oranları Hesapla" isteğini backend'e gönderip gelen oranları dinamik kartlara basmak.
3. Östenitik paslanmazlar seçildiğinde arayüzdeki kartların çözeltiye alma moduna geçmesini sağlamak.

---
*Bu doküman, Faz Atlası projesinin bir akademik prototipten endüstriyel standartta bir SaaS/Mühendislik yazılımına dönüştürülmesi için hazırlanmış eksiksiz teknik şartnamedir.*
