# Faz Atlası 2.0 — backend

[English](README.md) · **Türkçe**

Çelik kütüphanesi (SQLite/PostgreSQL), alaşım aileleri, sınır izlemeli dikey kesitler ve tek nokta CALPHAD dengesi
için FastAPI servisi.

## Kurulum (yerel)

```bash
.venv/Scripts/pip install -r backend/requirements.txt -r backend/requirements-api.txt
.venv/Scripts/python backend/build_db.py                      # backend/data/faz_atlasi.db
.venv/Scripts/python backend/trace_families.py --celik 42CrMo4 # bir ailenin kesiti
.venv/Scripts/python -m uvicorn faz_atlasi.api.main:app --app-dir backend --port 8000
```

API belgeleri: http://localhost:8000/docs. Testler: `.venv/Scripts/python -m pytest backend/tests -q`.

TDB (`hesap/tdb/mc_fe_pycalphad.tdb`) depoda yok; ana README'deki adresten indirilip `hesap/tdb_temizle.py` ile üretilir.

## Uç noktalar

| Uç nokta | Açıklama |
|---|---|
| `GET /api/v1/steels?q=&system=&steel_class=&limit=&offset=` | Her normla arama (42CrMo4, 1.7225, 4140, SCM440, G41400); `system=JIS` o normdaki adlarla listeler |
| `GET /api/v1/steels/{id}` | Normlar, bileşim aralıkları, sınıf, aile, kaynaklar |
| `GET /api/v1/families/{id}` | Aile bileşimi, üye sayısı, kesit durumu |
| `GET /api/v1/isopleth/{family_id}` | Kesit: satır bölgeleri (`rows`) ve sınır çizgileri (`lines`) |
| `GET /api/v1/steels/{id}/heat-treatment` | Sınıfa göre ısıl işlem rejimi (aşağıda) |
| `GET /api/v1/steels/{id}/family-fit` | Çeliğin kritik sıcaklıklarının ailesinin kesitindekilerden farkı (aşağıda) |
| `POST /api/v1/heat-treatment` | `{"composition": {...}, "steel_class": null}` → kullanıcı bileşimi için aynı rejim; sınıf verilmezse kestirilir |
| `POST /api/v1/equilibrium/point` | `{"composition": {"C": 0.42, "Cr": 1.05, ...}, "T": 760}` → faz oranları, fazlardaki karbon, faz bileşimleri |

## Isıl işlem rejimi (`faz_atlasi/calc/isil_islem.py`)

| Mod | Sınıf | Döndürülen |
|---|---|---|
| `transformation` | karbon/düşük alaşımlı, martenzitik paslanmaz | Ae1, Ae3, karbür çözünme, δ-ferrit başlangıcı (CALPHAD); sertleştirme Ae3 + 30–50 °C; Ms (Andrews) |
| `solution_annealing` | östenitik paslanmaz | A1/A3 gizlenir (`hide`); çözeltiye alma 1050–1100 °C; hassaslaşma 500–800 °C ve risk (C ≤ %0,03 ya da Ti ≥ 5C / Nb ≥ 10C → düşük); M23C6 ve σ çözünme (CALPHAD); Ms (Eichelman–Hull), Md30 (Angel) |
| `duplex` | dupleks | çözeltiye alma 1020–1100 °C, σ çözünme, 475 °C gevrekleşmesi |
| `ferritic` | ferritik paslanmaz | tavlama 750–850 °C, 475 °C gevrekleşmesi, σ |
| `no_transformation` | Hadfield, Fe-Ni, yarı östenitik | sadece CALPHAD sıcaklıkları |

CALPHAD sıcaklıkları denge değerleridir (Ac/Ar değil): 450–1350 °C arası 50 °C tarama + ±2 °C'ye ikiye bölme.
Bir çelik ilk sorulduğunda 1–16 s (yeni alaşım sistemi derleniyorsa uzun), sonra önbellekten.

## Alt aileler ve çelik–aile uyumu (`calc/sapma.py`, `library/alt_aile.py`)

Aile kesiti ailenin (kurucu çeliğin) alaşımıyla hesaplanır; bileşim toleransı içindeki farklar aynı yöne
toplanınca bir çeliğin kritik sıcaklıkları kesittekilerden 15–20 °C ayrışabiliyor. Bu yüzden her çelik ailesine
karşı CALPHAD ile ölçülür: çeliğin kendi bileşimi ile aile bileşiminde, çeliğin karbonunda Ae1, Ae3, karbür ve σ
çözünme, δ-ferrit başlangıcı (aynı yöntem, ±2 °C).

* **Fark > 5 °C** (kesitin satır aralığı) ya da bir geçiş birinde var ötekinde yok: çelik ailesinden ayrılır. Önce
  bileşimce yakın başka bir mevcut aileye, sonra bu turda açılan alt ailelere ölçülür; uymazsa kendi bileşimiyle
  **alt aile** kurar (`alloy_families.parent_id` = eski aile). Ayrılma nedeni `parent_fit` olarak saklanır.
* **Fark ≤ 5 °C**: çelik ailede kalır; arayüz kesitin sıcaklık eksenini bu çiftlerle parça parça doğrusal kaydırır
  (`web/kesit.js: sicaklikEsle`). Çeliğin karbonunda çizgiler çeliğin kendi değerine oturur.
* Kaynakta Mn/Si verilmemiş çeliklere `missing_elements` ile uyarı gösterilir (hesapta 0 sayılıyorlar).

```bash
.venv/Scripts/python backend/split_families.py                # ölç -> backend/data/alt_aileler.json (veritabanına yazmaz)
.venv/Scripts/python backend/split_families.py --uygula       # alt aileleri kur, çelikleri taşı (trace bitince)
.venv/Scripts/python backend/trace_families.py --eksik --uyarlanir   # yeni alt ailelerin kesitleri
```

`build_db.py` veritabanını baştan kurarken `alt_aileler.json`'u uygular (aile yapısı ölçümden sonra değiştiyse o kayıtlar
atlanır ve bildirilir). Ölçülmemiş çelik için `GET /api/v1/steels/{id}/family-fit` ölçüp saklar.

## Ölçümler (2026-11-02, 12 çekirdekli dizüstü; aynı anda başka bir hesap 4 çekirdek kullanıyordu)

| İşlem | Ölçülen |
|---|---|
| Tek nokta, ilk istek (TDB okuma + derleme) | ~15 s; açılışta `FAZ_WARMUP` ile önceden yapılır |
| Aynı alaşım sisteminin yeni bileşen kümesi, ilk istek | 2–5 s (model derleme; sonra bellekte) |
| Tek nokta, sıcak (42CrMo4, 5 bileşen) | ~100–140 ms |
| Tek nokta, sıcak (304, 6 bileşen) | ~70–90 ms |
| Önbellekten | <1 ms |
| Kesit, sınır izleme, 42CrMo4, 111 satır, 4 işlem | ~105 s, 4 800 nokta (eski tam ızgara: ~133 s, ~14 000 nokta) |

Kesit, eski ızgarayla 111 satırın 106'sında aynı bölge dizisini veriyor; sınırlar arasındaki fark medyan 0,001, en çok 0,018
(ağ.% C). Farklı 5 satırdaki fark, genişliği <0,01 olan dört fazlı ince şeritlerden kaynaklanıyor.

Dokümandaki "20 ms tek nokta" ve "10–15 s kesit" hedefleri pycalphad 0.11.2'nin `equilibrium()` çağrısıyla
tutmuyor: sürenin ~yarısı başlangıç ızgarası (`calculate`), ~%40'ı çözücü ve dışbükey zarf. Izgara yoğunluğu
düşürülünce (pdens 30) ~%40 hızlanıyor ama düşük sıcaklıkta çok karbürlü bölgelerde yanlış faz kümesi veriyor;
bu yüzden tek nokta varsayılan yoğunlukla, kesit taraması hızlı yoğunlukla + bölge başına doğrulamayla yapılıyor.
pycalphad'ın kendi `IsoplethStrategy`'si aynı kesitte ~300 s sürdü.

## Bilinen sınırlar

* `mc_fe_pycalphad.tdb` sadece C, Cr, Cu, Mn, Mo, Ni, Si, V, W içeriyor. N, Ti, Nb, Al, Co, B hesaba girmez; yanıtta
  `ignored_elements` olarak bildirilir. 304/316'daki N, 321'deki Ti, 2205'teki N bu yüzden ihmal ediliyor.
* pycalphad iş parçacığı güvenli değil: çağrılar kilitle sıraya girer; ölçekleme konteyner sayısıyla yapılır.
* Dockerfile ve docker-compose yazıldı ama bu makinede Docker yok; denenmedi. PostgreSQL ile de denenmedi.
