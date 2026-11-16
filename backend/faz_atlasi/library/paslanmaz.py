"""
Paslanmaz çelikler — EN 10088-1/-3 döküm analizi aralıkları.

Biçim celik_kutuphanesi.py ile aynıdır, ek olarak sınıf ve norm listesi:
  (EN adı, W.Nr., sınıf, kullanım TR, kullanım EN, aralıklar, [(sistem, kod, approx), ...])
Aralık: element -> (min, max) ya da (min, max, nominal). Sadece üst sınırı olanlarda min = 0 ve tipik nominal.
Ti'li kalitelerde (321, 316Ti) standart alt sınır 5×C'dir; burada nominal C için hesaplanmış değer yazıldı.
Değerler satın alınan güncel EN 10088 metniyle karşılaştırılıp doğrulanmalıdır.
"""

SI1 = (0, 1.00, 0.40)
MN1 = (0, 1.00, 0.60)
MN2 = (0, 2.00, 1.20)
N10 = (0, 0.10, 0.05)

PASLANMAZLAR = [
    # --- Martenzitik (A1 bandı, M23C6 çözünmesi ve Ms normal hesaplanır)
    ('X12Cr13', '1.4006', 'martensitic_stainless', 'Türbin kanadı, vana, cıvata', 'Turbine blades, valves, bolts',
     {'C': (0.08, 0.15), 'Si': SI1, 'Mn': (0, 1.50, 0.60), 'Cr': (11.5, 13.5), 'Ni': (0, 0.75, 0.30)},
     [('AISI', '410', False), ('UNS', 'S41000', False), ('JIS', 'SUS410', True)]),
    ('X20Cr13', '1.4021', 'martensitic_stainless', 'Pompa mili, vana, cerrahi alet', 'Pump shafts, valves, surgical tools',
     {'C': (0.16, 0.25), 'Si': SI1, 'Mn': (0, 1.50, 0.60), 'Cr': (12.0, 14.0)},
     [('AISI', '420', False), ('UNS', 'S42000', False), ('JIS', 'SUS420J1', True)]),
    ('X46Cr13', '1.4034', 'martensitic_stainless', 'Bıçak, kesici, rulman (korozif ortam)', 'Knives, cutters, corrosion-resistant bearings',
     {'C': (0.43, 0.50), 'Si': SI1, 'Mn': MN1, 'Cr': (12.5, 14.5)},
     [('AISI', '420C', True), ('JIS', 'SUS420J2', True)]),
    ('X90CrMoV18', '1.4112', 'martensitic_stainless', 'Bıçak, rulman, valf yuvası', 'Knives, bearings, valve seats',
     {'C': (0.85, 0.95), 'Si': SI1, 'Mn': MN1, 'Cr': (17.0, 19.0), 'Mo': (0.90, 1.30), 'V': (0.07, 0.12)},
     [('AISI', '440B', True), ('JIS', 'SUS440B', True)]),

    # --- Ferritik
    ('X6Cr17', '1.4016', 'ferritic_stainless', 'Mutfak eşyası, dekoratif sac', 'Kitchenware, decorative sheet',
     {'C': (0, 0.08, 0.05), 'Si': SI1, 'Mn': MN1, 'Cr': (16.0, 18.0)},
     [('AISI', '430', False), ('UNS', 'S43000', False), ('JIS', 'SUS430', True)]),

    # --- Östenitik (A1/A3 yok; çözeltiye alma ve hassaslaşma modu)
    ('X5CrNi18-10', '1.4301', 'austenitic_stainless', 'Gıda, kimya, mimari; genel amaçlı paslanmaz', 'Food, chemical, architecture; general-purpose stainless',
     {'C': (0, 0.07, 0.04), 'Si': SI1, 'Mn': MN2, 'Cr': (17.5, 19.5), 'Ni': (8.0, 10.5), 'N': N10},
     [('AISI', '304', False), ('UNS', 'S30400', False), ('JIS', 'SUS304', True)]),
    ('X2CrNi18-9', '1.4307', 'austenitic_stainless', 'Kaynaklı paslanmaz yapı, tank', 'Welded stainless structures, tanks',
     {'C': (0, 0.030, 0.02), 'Si': SI1, 'Mn': MN2, 'Cr': (17.5, 19.5), 'Ni': (8.0, 10.5), 'N': N10},
     [('AISI', '304L', False), ('UNS', 'S30403', False), ('JIS', 'SUS304L', True)]),
    ('X5CrNiMo17-12-2', '1.4401', 'austenitic_stainless', 'Deniz, kimya, ilaç ekipmanı', 'Marine, chemical, pharmaceutical equipment',
     {'C': (0, 0.07, 0.04), 'Si': SI1, 'Mn': MN2, 'Cr': (16.5, 18.5), 'Ni': (10.0, 13.0), 'Mo': (2.00, 2.50), 'N': N10},
     [('AISI', '316', False), ('UNS', 'S31600', False), ('JIS', 'SUS316', True)]),
    ('X2CrNiMo17-12-2', '1.4404', 'austenitic_stainless', 'Kaynaklı kimya ve deniz ekipmanı', 'Welded chemical and marine equipment',
     {'C': (0, 0.030, 0.02), 'Si': SI1, 'Mn': MN2, 'Cr': (16.5, 18.5), 'Ni': (10.0, 13.0), 'Mo': (2.00, 2.50), 'N': N10},
     [('AISI', '316L', False), ('UNS', 'S31603', False), ('JIS', 'SUS316L', True)]),
    ('X6CrNiTi18-10', '1.4541', 'austenitic_stainless', 'Yüksek sıcaklık, kaynaklı boru (Ti ile kararlı)', 'High temperature, welded tubing (Ti-stabilized)',
     {'C': (0, 0.08, 0.05), 'Si': SI1, 'Mn': MN2, 'Cr': (17.0, 19.0), 'Ni': (9.0, 12.0), 'Ti': (0.25, 0.70, 0.40)},
     [('AISI', '321', False), ('UNS', 'S32100', False), ('JIS', 'SUS321', True), ('GOST', '08X18N10T', True)]),
    ('X6CrNiMoTi17-12-2', '1.4571', 'austenitic_stainless', 'Kimya tesisi, ısı değiştirici (Ti ile kararlı)', 'Chemical plant, heat exchangers (Ti-stabilized)',
     {'C': (0, 0.08, 0.05), 'Si': SI1, 'Mn': MN2, 'Cr': (16.5, 18.5), 'Ni': (10.5, 13.5), 'Mo': (2.00, 2.50), 'Ti': (0.25, 0.70, 0.40)},
     [('AISI', '316Ti', False), ('UNS', 'S31635', False), ('JIS', 'SUS316Ti', True)]),

    # --- Dupleks
    ('X2CrNiMoN22-5-3', '1.4462', 'duplex_stainless', 'Petrokimya, deniz suyu, basınçlı kap', 'Petrochemical, seawater, pressure vessels',
     {'C': (0, 0.030, 0.02), 'Si': SI1, 'Mn': MN2, 'Cr': (21.0, 23.0), 'Ni': (4.5, 6.5), 'Mo': (2.50, 3.50), 'N': (0.10, 0.22)},
     [('UNS', 'S32205', False), ('UNS', 'S31803', True), ('TRADE', '2205', False)]),
]


def nominal(aralik):
    return {e: round(a[2] if len(a) == 3 else (a[0] + a[1]) / 2, 3) for e, a in aralik.items()}
