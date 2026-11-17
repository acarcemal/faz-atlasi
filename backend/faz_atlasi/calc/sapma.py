"""
Çelik–aile sapması: bir çeliğin kendi bileşimindeki kritik sıcaklıklar ile ailesinin kesitindekiler arasındaki fark.

Aile kesiti, ailenin (kurucu çeliğin) alaşım bileşimiyle hesaplanır; aynı kesiti kullanan çeliğin alaşımı tolerans
içinde farklıdır. Fark, iki bileşimin aynı karbonda (çeliğin nominal karbonu) aynı yöntemle (isil_islem._calphad:
50 °C tarama + ±2 °C ikiye bölme) bulunan sıcaklıkları karşılaştırılarak ölçülür:
  Ae1, Ae3, karbür çözünme, δ-ferrit başlangıcı, σ çözünme.

Kullanıldığı yerler:
  * library/alt_aile.py: ESIK'i aşan çelik ailesinden ayrılır (kendi kesiti olan alt aile).
  * Arayüz: kalan fark (≤ ESIK) çizimde düzeltilir — kesitin sıcaklık ekseni, ailenin bu sıcaklıkları çeliğin
    kendi değerlerine denk gelecek şekilde parça parça doğrusal kaydırılır (web/kesit.js: sicaklikEsle).
"""
from . import isil_islem

# °C. Kesitin satır aralığı (dT = 5 °C) kadar: bunun altındaki fark çizimde zaten ayırt edilemez.
ESIK = 5.0
ANAHTARLAR = ('Ae1', 'Ae3', 'carbide_solvus', 'delta_ferrite', 'sigma_solvus')
# İki bölmeli ölçümün kendi belirsizliği (her değer ±1 °C)
OLCUM_BELIRSIZLIGI = 2.0


def kritikler(ps, bilesim):
    """Bileşimin CALPHAD kritik sıcaklıkları {anahtar: °C ya da None}."""
    T, _ = isil_islem._calphad(ps, bilesim)
    return {k: T.get(k) for k in ANAHTARLAR}


def karsilastir(celik_T, aile_T, esik=ESIK):
    """
    İki kritik sıcaklık kümesinin farkı. Bir geçiş birinde var, ötekinde yoksa (ör. Ae1 tarama aralığının altına
    kaydı ya da bir karbür hiç çıkmıyor) kesitlerin yapısı farklı demektir: 'mismatch' olarak bildirilir ve
    tolerans dışı sayılır.
    """
    ciftler, uyumsuz = [], []
    for k in ANAHTARLAR:
        c, a = celik_T.get(k), aile_T.get(k)
        if c is None and a is None:
            continue
        if c is None or a is None:
            uyumsuz.append({'key': k, 'family': a, 'steel': c})
            continue
        ciftler.append({'key': k, 'family': a, 'steel': c, 'delta': c - a})
    en_buyuk = max((abs(p['delta']) for p in ciftler), default=0)
    return {
        'pairs': ciftler,
        'mismatch': uyumsuz,
        'max_abs_delta': en_buyuk,
        'within': not uyumsuz and en_buyuk <= esik,
        'threshold': esik,
    }


def olc(ps, celik_nom, aile_alasim):
    """
    celik_nom: çeliğin nominal bileşimi {element: ağ.%} (C dahil). aile_alasim: ailenin alaşım bileşimi (C hariç).
    Aile kesiti çeliğin karbonunda ölçülür.
    """
    C = celik_nom.get('C')
    if C is None:
        raise ValueError('çeliğin karbonu yok')
    sonuc = karsilastir(kritikler(ps, celik_nom), kritikler(ps, {**aile_alasim, 'C': C}))
    return {'C': C, **sonuc}
