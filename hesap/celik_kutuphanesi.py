"""
Çelik kütüphanesi — tek kaynak. Hem kesit hesabı (kesit_uret.py) hem web sayfası buradan beslenir.

  .venv/Scripts/python hesap/celik_kutuphanesi.py     # web/veri/celikler.js dosyasını yazar

Her çelik: (ad, malzeme no, AISI/SAE karşılığı, grup, standart, kullanım, aralıklar)
Aralık: element -> (min, max) ya da (min, max, nominal).
  - Nominal verilmezse aralığın ortası kullanılır.
  - Standartta sadece üst sınır varsa (ör. Si ≤ 0,40) min = 0 yazılır ve tipik değer nominal olarak verilir.
P, S, B, Al, N, Nb, Ti gibi elementler bu modelde yok; bu yüzden borlu ve Al'li (nitrürleme) çelikler listede değil.
Değerler ilgili EN/ISO standartlarındaki döküm (ladle) analizi aralıklarıdır; eğitim ve ön fikir amaçlıdır.
"""
import json, os

S40 = (0, 0.40, 0.25)    # Si ≤ 0,40 -> tipik 0,25
S60 = (0, 0.60, 0.40)    # dökümde Si ≤ 0,60 -> tipik 0,40

CELIKLER = [
    # --- Karbon (ıslah/genel) çelikleri — EN ISO 683-1 / EN 10083-2
    ('C10E', '1.1121', '1010', 'Karbon çeliği', 'EN ISO 683-3', 'Sementasyon, soğuk şekillendirme', {'C': (0.07, 0.13), 'Mn': (0.30, 0.60), 'Si': S40}),
    ('C15E', '1.1141', '1015', 'Karbon çeliği', 'EN ISO 683-3', 'Sementasyon, pim, burç', {'C': (0.12, 0.18), 'Mn': (0.30, 0.60), 'Si': S40}),
    ('C22E', '1.1151', '1020', 'Karbon çeliği', 'EN ISO 683-1', 'Kaynaklı yapı, mil, flanş', {'C': (0.17, 0.24), 'Mn': (0.40, 0.70), 'Si': S40}),
    ('C35E', '1.1181', '1035', 'Karbon çeliği', 'EN ISO 683-1', 'Mil, cıvata, dövme parça', {'C': (0.32, 0.39), 'Mn': (0.50, 0.80), 'Si': S40}),
    ('C45E', '1.1191', '1045', 'Karbon çeliği', 'EN ISO 683-1', 'Mil, dişli, makine parçası', {'C': (0.42, 0.50), 'Mn': (0.50, 0.80), 'Si': S40}),
    ('C55E', '1.1203', '1055', 'Karbon çeliği', 'EN ISO 683-1', 'Dişli, ray, aşınma parçası', {'C': (0.52, 0.60), 'Mn': (0.60, 0.90), 'Si': S40}),
    ('C60E', '1.1221', '1060', 'Karbon çeliği', 'EN ISO 683-1', 'Yay, bıçak, aşınma parçası', {'C': (0.57, 0.65), 'Mn': (0.60, 0.90), 'Si': S40}),
    ('28Mn6', '1.1170', '1527', 'Karbon çeliği', 'EN ISO 683-1', 'Dövme parça, mil', {'C': (0.25, 0.32), 'Mn': (1.30, 1.65), 'Si': S40}),
    ('S235JR', '1.0038', 'A36 (≈)', 'Yapı çeliği', 'EN 10025-2', 'Genel yapı, konstrüksiyon (tipik bileşim)', {'C': (0, 0.17, 0.12), 'Mn': (0, 1.40, 0.60), 'Si': (0, 0.30, 0.20)}),
    ('S355J2', '1.0577', 'A572 Gr.50 (≈)', 'Yapı çeliği', 'EN 10025-2', 'Kaynaklı yapı, köprü, vinç (tipik bileşim)', {'C': (0, 0.20, 0.17), 'Mn': (0, 1.60, 1.40), 'Si': (0, 0.55, 0.30)}),
    ('AISI 1018', '—', '1018', 'Karbon çeliği', 'SAE J403', 'Genel makine, soğuk çekme', {'C': (0.15, 0.20), 'Mn': (0.60, 0.90), 'Si': S40}),

    # --- Islah çelikleri — EN ISO 683-2
    ('25CrMo4', '1.7218', '4130', 'Islah çeliği', 'EN ISO 683-2', 'Basınçlı kap, boru, uçak parçası', {'C': (0.22, 0.29), 'Mn': (0.60, 0.90), 'Si': S40, 'Cr': (0.90, 1.20), 'Mo': (0.15, 0.30)}),
    ('34CrMo4', '1.7220', '4135', 'Islah çeliği', 'EN ISO 683-2', 'Mil, aks, tüp', {'C': (0.30, 0.37), 'Mn': (0.60, 0.90), 'Si': S40, 'Cr': (0.90, 1.20), 'Mo': (0.15, 0.30)}),
    ('42CrMo4', '1.7225', '4140', 'Islah çeliği', 'EN ISO 683-2', 'Mil, dişli, cıvata, krank', {'C': (0.38, 0.45), 'Mn': (0.60, 0.90), 'Si': S40, 'Cr': (0.90, 1.20), 'Mo': (0.15, 0.30)}),
    ('50CrMo4', '1.7228', '4150', 'Islah çeliği', 'EN ISO 683-2', 'Büyük kesitli mil, dişli', {'C': (0.46, 0.54), 'Mn': (0.50, 0.80), 'Si': S40, 'Cr': (0.90, 1.20), 'Mo': (0.15, 0.30)}),
    ('34Cr4', '1.7033', '5132', 'Islah çeliği', 'EN ISO 683-2', 'Mil, aks, direksiyon parçası', {'C': (0.30, 0.37), 'Mn': (0.60, 0.90), 'Si': S40, 'Cr': (0.90, 1.20)}),
    ('37Cr4', '1.7034', '5135', 'Islah çeliği', 'EN ISO 683-2', 'Mil, dişli, cıvata', {'C': (0.34, 0.41), 'Mn': (0.60, 0.90), 'Si': S40, 'Cr': (0.90, 1.20)}),
    ('41Cr4', '1.7035', '5140', 'Islah çeliği', 'EN ISO 683-2', 'Mil, dişli, krank', {'C': (0.38, 0.45), 'Mn': (0.60, 0.90), 'Si': S40, 'Cr': (0.90, 1.20)}),
    ('36CrNiMo4', '1.6511', '9840 (≈)', 'Islah çeliği', 'EN ISO 683-2', 'Yüksek mukavemetli mil, dişli', {'C': (0.32, 0.40), 'Mn': (0.50, 0.80), 'Si': S40, 'Cr': (0.90, 1.20), 'Ni': (0.90, 1.20), 'Mo': (0.15, 0.30)}),
    ('34CrNiMo6', '1.6582', '4340 (≈)', 'Islah çeliği', 'EN ISO 683-2', 'Ağır yüklü mil, krank, dişli', {'C': (0.30, 0.38), 'Mn': (0.50, 0.80), 'Si': S40, 'Cr': (1.30, 1.70), 'Ni': (1.30, 1.70), 'Mo': (0.15, 0.30)}),
    ('30CrNiMo8', '1.6580', '—', 'Islah çeliği', 'EN ISO 683-2', 'Çok büyük kesitli, yüksek tokluk', {'C': (0.26, 0.34), 'Mn': (0.50, 0.80), 'Si': S40, 'Cr': (1.80, 2.20), 'Ni': (1.80, 2.20), 'Mo': (0.30, 0.50)}),
    ('AISI 4340', '—', '4340', 'Islah çeliği', 'SAE J404', 'Uçak, ağır makine, yüksek mukavemet', {'C': (0.38, 0.43), 'Mn': (0.60, 0.80), 'Si': (0.15, 0.35), 'Cr': (0.70, 0.90), 'Ni': (1.65, 2.00), 'Mo': (0.20, 0.30)}),
    ('30CrMoV9', '1.7707', '—', 'Islah çeliği', 'EN 10085', 'Yüksek mukavemetli mil, nitrürlenebilir', {'C': (0.26, 0.34), 'Mn': (0.40, 0.70), 'Si': S40, 'Cr': (2.30, 2.70), 'Mo': (0.15, 0.25), 'V': (0.10, 0.20)}),
    ('31CrMo12', '1.8515', '—', 'Nitrürleme çeliği', 'EN 10085', 'Nitrürlenmiş dişli, kalıp parçası', {'C': (0.28, 0.35), 'Mn': (0.40, 0.70), 'Si': S40, 'Cr': (2.80, 3.30), 'Mo': (0.30, 0.50)}),

    # --- Sementasyon çelikleri — EN ISO 683-3
    ('16MnCr5', '1.7131', '5115', 'Sementasyon çeliği', 'EN ISO 683-3', 'Dişli, pim, mil (sementasyon)', {'C': (0.14, 0.19), 'Mn': (1.00, 1.30), 'Si': S40, 'Cr': (0.80, 1.10)}),
    ('20MnCr5', '1.7147', '5120', 'Sementasyon çeliği', 'EN ISO 683-3', 'Dişli, mil (sementasyon)', {'C': (0.17, 0.22), 'Mn': (1.10, 1.40), 'Si': S40, 'Cr': (1.00, 1.30)}),
    ('16NiCr4', '1.5714', '—', 'Sementasyon çeliği', 'EN ISO 683-3', 'Dişli, mil', {'C': (0.13, 0.19), 'Mn': (0.70, 1.00), 'Si': S40, 'Cr': (0.60, 1.00), 'Ni': (0.80, 1.10)}),
    ('17CrNi6-6', '1.5918', '—', 'Sementasyon çeliği', 'EN ISO 683-3', 'Ağır yüklü dişli', {'C': (0.14, 0.20), 'Mn': (0.50, 0.90), 'Si': S40, 'Cr': (1.40, 1.70), 'Ni': (1.40, 1.70)}),
    ('18CrNiMo7-6', '1.6587', '—', 'Sementasyon çeliği', 'EN ISO 683-3', 'Büyük, ağır yüklü dişli', {'C': (0.15, 0.21), 'Mn': (0.50, 0.90), 'Si': S40, 'Cr': (1.50, 1.80), 'Ni': (1.40, 1.70), 'Mo': (0.25, 0.35)}),
    ('20NiCrMo2-2', '1.6523', '8620', 'Sementasyon çeliği', 'EN ISO 683-3', 'Dişli, kam mili, pim', {'C': (0.17, 0.23), 'Mn': (0.65, 0.95), 'Si': S40, 'Cr': (0.35, 0.70), 'Ni': (0.40, 0.70), 'Mo': (0.15, 0.25)}),
    ('20MoCr4', '1.7321', '4118 (≈)', 'Sementasyon çeliği', 'EN ISO 683-3', 'Dişli, mil', {'C': (0.17, 0.23), 'Mn': (0.70, 1.00), 'Si': S40, 'Cr': (0.30, 0.60), 'Mo': (0.40, 0.50)}),
    ('14NiCrMo13-4', '1.6657', '9310 (≈)', 'Sementasyon çeliği', 'EN ISO 683-3', 'Havacılık dişlisi, yüksek tokluk', {'C': (0.11, 0.17), 'Mn': (0.30, 0.60), 'Si': S40, 'Cr': (0.80, 1.10), 'Ni': (3.00, 3.50), 'Mo': (0.20, 0.30)}),
    ('AISI 9310', '—', '9310', 'Sementasyon çeliği', 'SAE J404', 'Havacılık dişlisi', {'C': (0.07, 0.13), 'Mn': (0.45, 0.65), 'Si': (0.15, 0.35), 'Cr': (1.00, 1.40), 'Ni': (3.00, 3.50), 'Mo': (0.08, 0.15)}),

    # --- Yay çelikleri — EN 10089 / EN 10132
    ('C75S', '1.1248', '1075', 'Yay çeliği', 'EN 10132-4', 'Yassı yay, testere, bıçak', {'C': (0.70, 0.80), 'Mn': (0.60, 0.90), 'Si': (0.15, 0.35)}),
    ('C85S', '1.1269', '1086', 'Yay çeliği', 'EN 10132-4', 'Yay, testere bıçağı', {'C': (0.80, 0.90), 'Mn': (0.40, 0.70), 'Si': (0.15, 0.35)}),
    ('C100S', '1.1274', '1095', 'Yay çeliği', 'EN 10132-4', 'Yay, kesici bıçak', {'C': (0.95, 1.05), 'Mn': (0.30, 0.60), 'Si': (0.15, 0.35)}),
    ('38Si7', '1.5023', '—', 'Yay çeliği', 'EN 10089', 'Yaylı rondela, klips', {'C': (0.35, 0.42), 'Mn': (0.50, 0.80), 'Si': (1.50, 1.80)}),
    ('56Si7', '1.5026', '9255', 'Yay çeliği', 'EN 10089', 'Yaprak yay, helezon yay', {'C': (0.52, 0.60), 'Mn': (0.60, 0.90), 'Si': (1.60, 2.00)}),
    ('54SiCr6', '1.7102', '9254', 'Yay çeliği', 'EN 10089', 'Süspansiyon yayı, valf yayı', {'C': (0.51, 0.59), 'Mn': (0.50, 0.80), 'Si': (1.20, 1.60), 'Cr': (0.50, 0.80)}),
    ('60SiCr7', '1.7108', '9262', 'Yay çeliği', 'EN 10089', 'Yaprak yay, burulma çubuğu', {'C': (0.56, 0.64), 'Mn': (0.70, 1.00), 'Si': (1.50, 2.00), 'Cr': (0.20, 0.45)}),
    ('51CrV4', '1.8159', '6150', 'Yay çeliği', 'EN 10089', 'Yaprak yay, ağır yay, dişli', {'C': (0.47, 0.55), 'Mn': (0.70, 1.10), 'Si': S40, 'Cr': (0.90, 1.20), 'V': (0.10, 0.25)}),
    ('52CrMoV4', '1.7701', '—', 'Yay çeliği', 'EN 10089', 'Büyük kesitli ağır yay', {'C': (0.48, 0.56), 'Mn': (0.70, 1.10), 'Si': S40, 'Cr': (0.90, 1.20), 'Mo': (0.15, 0.30), 'V': (0.10, 0.20)}),

    # --- Rulman çelikleri — EN ISO 683-17
    ('100Cr6', '1.3505', '52100', 'Rulman çeliği', 'EN ISO 683-17', 'Bilye, makara, rulman bileziği', {'C': (0.93, 1.05), 'Mn': (0.25, 0.45), 'Si': (0.15, 0.35), 'Cr': (1.35, 1.60)}),
    ('100CrMnSi6-4', '1.3520', '—', 'Rulman çeliği', 'EN ISO 683-17', 'Kalın kesitli rulman bileziği', {'C': (0.93, 1.05), 'Mn': (1.00, 1.20), 'Si': (0.45, 0.75), 'Cr': (1.40, 1.65)}),
    ('100CrMo7-3', '1.3536', '—', 'Rulman çeliği', 'EN ISO 683-17', 'Büyük rulman bileziği', {'C': (0.93, 1.05), 'Mn': (0.60, 0.80), 'Si': (0.15, 0.35), 'Cr': (1.65, 1.95), 'Mo': (0.20, 0.35)}),

    # --- Takım çelikleri (düşük alaşımlı) — ISO 4957
    ('C45U', '1.1730', '1045 (≈)', 'Takım çeliği', 'ISO 4957', 'Kalıp gövdesi, el aleti', {'C': (0.42, 0.50), 'Mn': (0.60, 0.80), 'Si': (0.15, 0.40)}),
    ('C80U', '1.1525', 'W1-8 (≈)', 'Takım çeliği', 'ISO 4957', 'Keski, zımba, el aleti', {'C': (0.75, 0.85), 'Mn': (0.10, 0.35), 'Si': (0.10, 0.30)}),
    ('C105U', '1.1545', 'W1-10 (≈)', 'Takım çeliği', 'ISO 4957', 'Eğe, kesici, zımba', {'C': (1.00, 1.10), 'Mn': (0.10, 0.40), 'Si': (0.10, 0.30)}),
    ('102Cr6', '1.2067', 'L3 (≈)', 'Takım çeliği', 'ISO 4957', 'Mastar, ölçü aleti, zımba', {'C': (0.95, 1.10), 'Mn': (0.25, 0.40), 'Si': (0.15, 0.35), 'Cr': (1.35, 1.65)}),
    ('90MnCrV8', '1.2842', 'O2', 'Takım çeliği', 'ISO 4957', 'Kesme kalıbı, mastar (yağda sertleşen)', {'C': (0.85, 0.95), 'Mn': (1.80, 2.20), 'Si': (0.10, 0.40), 'Cr': (0.20, 0.50), 'V': (0.05, 0.20)}),
    ('100MnCrW4', '1.2510', 'O1', 'Takım çeliği', 'ISO 4957', 'Kesme kalıbı, ölçü aleti', {'C': (0.90, 1.05), 'Mn': (1.00, 1.20), 'Si': (0.15, 0.35), 'Cr': (0.50, 0.70), 'W': (0.50, 0.70), 'V': (0.05, 0.15)}),
    ('60WCrV8', '1.2550', 'S1 (≈)', 'Takım çeliği', 'ISO 4957', 'Darbe takımı, makas bıçağı, keski', {'C': (0.55, 0.65), 'Mn': (0.15, 0.45), 'Si': (0.70, 1.00), 'Cr': (0.90, 1.20), 'W': (1.70, 2.20), 'V': (0.10, 0.20)}),
    ('40CrMnMo7', '1.2311', 'P20', 'Takım çeliği', 'ISO 4957', 'Plastik enjeksiyon kalıbı', {'C': (0.35, 0.45), 'Mn': (1.30, 1.60), 'Si': (0.20, 0.40), 'Cr': (1.80, 2.10), 'Mo': (0.15, 0.25)}),
    ('40CrMnNiMo8-6-4', '1.2738', 'P20+Ni', 'Takım çeliği', 'ISO 4957', 'Büyük plastik kalıp', {'C': (0.35, 0.45), 'Mn': (1.30, 1.60), 'Si': (0.20, 0.40), 'Cr': (1.80, 2.10), 'Ni': (0.90, 1.20), 'Mo': (0.15, 0.25)}),
    ('45NiCrMo16', '1.2767', '6F7 (≈)', 'Takım çeliği', 'ISO 4957', 'Bükme/kesme kalıbı, yüksek tokluk', {'C': (0.40, 0.50), 'Mn': (0.20, 0.50), 'Si': (0.10, 0.40), 'Cr': (1.20, 1.50), 'Ni': (3.80, 4.30), 'Mo': (0.15, 0.35)}),
    ('55NiCrMoV7', '1.2714', 'L6 (≈)', 'Takım çeliği', 'ISO 4957', 'Dövme kalıbı (sıcak iş, düşük alaşım)', {'C': (0.50, 0.60), 'Mn': (0.60, 0.90), 'Si': (0.10, 0.40), 'Cr': (0.80, 1.20), 'Ni': (1.50, 1.80), 'Mo': (0.35, 0.55), 'V': (0.05, 0.15)}),

    # --- Döküm çelikleri — EN 10293 / EN 10213
    ('GP240GH', '1.0619', 'WCB (≈)', 'Döküm çeliği', 'EN 10213', 'Vana gövdesi, basınçlı döküm (GS-C25)', {'C': (0.18, 0.23), 'Mn': (0.50, 1.20, 0.80), 'Si': S60}),
    ('G20Mn5', '1.6220', '—', 'Döküm çeliği', 'EN 10293', 'Kaynaklı döküm yapı parçası', {'C': (0.17, 0.23), 'Mn': (1.00, 1.60), 'Si': S60}),
    ('G28Mn6', '1.1165', '—', 'Döküm çeliği', 'EN 10293', 'Islah edilebilir döküm', {'C': (0.25, 0.32), 'Mn': (1.20, 1.80), 'Si': S60}),
    ('G34CrMo4', '1.7230', '4135 (≈)', 'Döküm çeliği', 'EN 10293', 'Islah edilmiş döküm parça', {'C': (0.30, 0.37), 'Mn': (0.50, 0.80), 'Si': S60, 'Cr': (0.80, 1.20), 'Mo': (0.15, 0.30)}),
    ('G42CrMo4', '1.7231', '4140 (≈)', 'Döküm çeliği', 'EN 10293', 'Yüksek mukavemetli döküm parça', {'C': (0.38, 0.45), 'Mn': (0.60, 1.00), 'Si': S60, 'Cr': (0.80, 1.20), 'Mo': (0.15, 0.30)}),
    ('G17CrMo5-5', '1.7357', 'WC6 (≈)', 'Döküm çeliği', 'EN 10213', 'Sıcağa dayanıklı vana, türbin gövdesi', {'C': (0.15, 0.20), 'Mn': (0.50, 1.00), 'Si': S60, 'Cr': (1.00, 1.50), 'Mo': (0.45, 0.65)}),
    ('G17CrMo9-10', '1.7379', 'WC9 (≈)', 'Döküm çeliği', 'EN 10213', 'Yüksek sıcaklık vana gövdesi', {'C': (0.13, 0.20), 'Mn': (0.50, 0.90), 'Si': S60, 'Cr': (2.00, 2.50), 'Mo': (0.90, 1.20)}),
]

ELEMENT_SIRASI = ['Mn', 'Si', 'Cr', 'Ni', 'Mo', 'V', 'W', 'Cu']

# İngilizce arayüz için grup ve kullanım alanları (çeviri değil, İngilizce literatürdeki karşılık)
GRUP_EN = {
    'Karbon çeliği': 'Carbon steel', 'Yapı çeliği': 'Structural steel', 'Islah çeliği': 'Quenched & tempered steel',
    'Nitrürleme çeliği': 'Nitriding steel', 'Sementasyon çeliği': 'Case-hardening steel', 'Yay çeliği': 'Spring steel',
    'Rulman çeliği': 'Bearing steel', 'Takım çeliği': 'Tool steel', 'Döküm çeliği': 'Cast steel',
}
KULLANIM_EN = {
    'C10E': 'Case hardening, cold forming', 'C15E': 'Case hardening, pins, bushings',
    'C22E': 'Welded structures, shafts, flanges', 'C35E': 'Shafts, bolts, forgings', 'C45E': 'Shafts, gears, machine parts',
    'C55E': 'Gears, rails, wear parts', 'C60E': 'Springs, blades, wear parts', '28Mn6': 'Forgings, shafts',
    'S235JR': 'General structural steel (typical composition)', 'S355J2': 'Welded structures, bridges, cranes (typical composition)',
    'AISI 1018': 'General machining, cold-drawn bar',
    '25CrMo4': 'Pressure vessels, tubing, aircraft parts', '34CrMo4': 'Shafts, axles, tubes',
    '42CrMo4': 'Shafts, gears, bolts, crankshafts', '50CrMo4': 'Large-section shafts, gears',
    '34Cr4': 'Shafts, axles, steering parts', '37Cr4': 'Shafts, gears, bolts', '41Cr4': 'Shafts, gears, crankshafts',
    '36CrNiMo4': 'High-strength shafts, gears', '34CrNiMo6': 'Heavy-duty shafts, crankshafts, gears',
    '30CrNiMo8': 'Very large sections, high toughness', 'AISI 4340': 'Aircraft, heavy machinery, high strength',
    '30CrMoV9': 'High-strength shafts, nitridable', '31CrMo12': 'Nitrided gears, die components',
    '16MnCr5': 'Gears, pins, shafts (carburized)', '20MnCr5': 'Gears, shafts (carburized)', '16NiCr4': 'Gears, shafts',
    '17CrNi6-6': 'Heavy-duty gears', '18CrNiMo7-6': 'Large, heavy-duty gears', '20NiCrMo2-2': 'Gears, camshafts, pins',
    '20MoCr4': 'Gears, shafts', '14NiCrMo13-4': 'Aerospace gears, high toughness', 'AISI 9310': 'Aerospace gears',
    'C75S': 'Flat springs, saws, blades', 'C85S': 'Springs, saw blades', 'C100S': 'Springs, cutting blades',
    '38Si7': 'Spring washers, clips', '56Si7': 'Leaf springs, coil springs', '54SiCr6': 'Suspension springs, valve springs',
    '60SiCr7': 'Leaf springs, torsion bars', '51CrV4': 'Leaf springs, heavy springs, gears', '52CrMoV4': 'Large-section heavy springs',
    '100Cr6': 'Balls, rollers, bearing rings', '100CrMnSi6-4': 'Thick-section bearing rings', '100CrMo7-3': 'Large bearing rings',
    'C45U': 'Die holders, hand tools', 'C80U': 'Chisels, punches, hand tools', 'C105U': 'Files, cutters, punches',
    '102Cr6': 'Gauges, measuring tools, punches', '90MnCrV8': 'Blanking dies, gauges (oil-hardening)',
    '100MnCrW4': 'Blanking dies, measuring tools', '60WCrV8': 'Shock-resisting tools, shear blades, chisels',
    '40CrMnMo7': 'Plastic injection molds', '40CrMnNiMo8-6-4': 'Large plastic molds',
    '45NiCrMo16': 'Bending and blanking dies, high toughness', '55NiCrMoV7': 'Forging dies (hot work, low alloy)',
    'GP240GH': 'Valve bodies, pressure castings (GS-C25)', 'G20Mn5': 'Weldable structural castings',
    'G28Mn6': 'Heat-treatable castings', 'G34CrMo4': 'Quenched and tempered castings', 'G42CrMo4': 'High-strength castings',
    'G17CrMo5-5': 'Heat-resistant valve and turbine casings', 'G17CrMo9-10': 'High-temperature valve bodies',
}


def nominal(aralik):
    out = {}
    for e, a in aralik.items():
        out[e] = round(a[2] if len(a) == 3 else (a[0] + a[1]) / 2, 3)
    return out


def alas_anahtari(nom):
    """Kesitin anahtarı: sadece alaşım elementleri (karbon kesit ekseni). Web tarafı da aynı biçimi üretir."""
    return '_'.join(f"{e}{nom[e]:g}" for e in ELEMENT_SIRASI if nom.get(e, 0) > 0) or 'saf'


def liste():
    out = []
    for ad, no, aisi, grup, std, kullanim, aralik in CELIKLER:
        nom = nominal(aralik)
        assert grup in GRUP_EN and ad in KULLANIM_EN, f'İngilizce karşılık eksik: {ad}'
        out.append({
            'ad': ad, 'no': no, 'aisi': aisi, 'grup': grup, 'std': std, 'kullanim': kullanim,
            'grup_en': GRUP_EN[grup], 'kullanim_en': KULLANIM_EN[ad],
            'aralik': {e: [a[0], a[1]] for e, a in aralik.items()},
            'nominal': nom,
            'anahtar': alas_anahtari(nom),
        })
    return out


if __name__ == '__main__':
    l = liste()
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web', 'veri', 'celikler.js')
    with open(yol, 'w', encoding='utf-8') as f:
        f.write('// hesap/celik_kutuphanesi.py ile üretildi — elle düzenleme yapmayın\n')
        f.write('window.CELIK_KUTUPHANE=')
        json.dump(l, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    print(f'{len(l)} çelik, {len({c["anahtar"] for c in l})} farklı alaşım (kesit) -> {os.path.abspath(yol)}')
