"""
Mikroyapı sınıfı (steels.steel_class) ve grup adı.

Öncelik: kütüphanede elle verilmiş sınıf > veri setinin kendi sınıfı (GOST seti) > bileşimden kestirim.
Kestirim kaba bir kuraldır (Schaeffler diyagramının özeti); kaynağı 'heuristic' olarak işaretlenir.
"""

# GOST setindeki (Mendeley 10.17632/mfhvdv4b8z.1) 'Class' sütunu
_GOST_SINIF = {
    'P': 'carbon_low_alloy', 'FP': 'carbon_low_alloy',
    'A': 'austenitic_stainless', 'AF': 'duplex_stainless', 'AM': 'semi_austenitic_stainless',
    'M': 'martensitic_stainless', 'FM': 'martensitic_stainless', 'F': 'ferritic_stainless',
    'FeNi': 'fe_ni_alloy',
}

PASLANMAZ_CR = 10.5


def from_dataset(kod, nom):
    """GOST setinin sınıfını bileşimle tutarlı hale getirir (ör. Cr<10,5 olan 'M' paslanmaz değildir)."""
    s = _GOST_SINIF[kod]
    cr = nom.get('Cr', 0)
    if s.endswith('_stainless') and cr < PASLANMAZ_CR:
        return 'austenitic_other' if s == 'austenitic_stainless' else 'carbon_low_alloy'
    return s


def heuristic(nom):
    cr, ni, mn, c = (nom.get(e, 0) for e in ('Cr', 'Ni', 'Mn', 'C'))
    if ni >= 25 and cr < 25:
        return 'fe_ni_alloy'
    if cr < PASLANMAZ_CR:
        return 'austenitic_other' if mn >= 10 or ni >= 15 else 'carbon_low_alloy'
    if ni >= 6 or (ni + 0.5 * mn + 30 * nom.get('N', 0)) >= 8:
        return 'austenitic_stainless'
    if ni >= 3.5 and cr >= 20:
        return 'duplex_stainless'
    if c >= 0.10 or ni >= 1.5:
        return 'martensitic_stainless'
    return 'ferritic_stainless'


_GRUP = {
    'martensitic_stainless': ('Martenzitik paslanmaz', 'Martensitic stainless'),
    'ferritic_stainless': ('Ferritik paslanmaz', 'Ferritic stainless'),
    'austenitic_stainless': ('Östenitik paslanmaz', 'Austenitic stainless'),
    'duplex_stainless': ('Dupleks paslanmaz', 'Duplex stainless'),
    'semi_austenitic_stainless': ('Yarı östenitik paslanmaz', 'Semi-austenitic stainless'),
    'austenitic_other': ('Östenitik çelik (paslanmaz değil)', 'Austenitic steel (non-stainless)'),
    'fe_ni_alloy': ('Fe-Ni alaşımı', 'Fe-Ni alloy'),
}


def group_for(sinif, nom, dokum=False):
    """Veri setinden gelen çelikler için grup adı (TR, EN)."""
    if sinif in _GRUP:
        tr, en = _GRUP[sinif]
    else:
        alasim = sum(v for e, v in nom.items() if e not in ('C', 'P', 'S', 'Si', 'Mn'))
        tr, en = ('Karbon çeliği', 'Carbon steel') if alasim < 0.5 and nom.get('Mn', 0) < 1.65 else \
                 ('Düşük alaşımlı çelik', 'Low-alloy steel') if alasim < 5 else ('Alaşımlı çelik', 'Alloy steel')
    if dokum:
        tr, en = f'{tr} (döküm)', f'{en} (cast)'
    return tr, en


def eksik_elementler(nom):
    """Her çelikte bulunan ama kaynakta verilmemiş (hesapta 0 sayılan) elementler. Açık veri setleri sakinleştirilmiş
    karbon çeliklerinde Si'yi çoğu zaman vermiyor; Si kritik sıcaklıkları birkaç derece ile ~15 °C arası etkiler."""
    return [e for e in ('Mn', 'Si') if not nom.get(e)]
