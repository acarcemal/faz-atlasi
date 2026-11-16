"""
Çelik sınıfına göre ısıl işlem rejimi.

  transformation      karbon / düşük alaşımlı ve martenzitik paslanmaz: Ae1, Ae3 (ya da Acm), karbür çözünmesi, Ms
  solution_annealing  östenitik paslanmaz: A1/A3 yok; çözeltiye alma tavı, hassaslaşma riski, sigma, Md30 ve Ms
  duplex              dupleks paslanmaz: çözeltiye alma tavı, sigma aralığı, 475 °C gevrekleşmesi
  ferritic            ferritik paslanmaz: sertleşmez; tavlama, 475 °C gevrekleşmesi, sigma
  no_transformation   Hadfield, Fe-Ni, yarı östenitik: sadece CALPHAD sıcaklıkları (empirik bağıntılar geçerli değil)

Kritik sıcaklıklar çeliğin nominal bileşiminde CALPHAD ile bulunur (denge değerleri; ısıtma/soğuma hızına bağlı
Ac/Ar değerleri değildir): 450–1350 °C arası 50 °C'lik tarama, sonra her geçiş ikiye bölünerek ±2 °C'ye daraltılır.
Tek nokta servisi önbellekli olduğu için aynı çelik ikinci kez sorulduğunda hesap tekrarlanmaz.
"""
from .point import PointService

KARBURLER = {'C', 'K7', 'K23', 'K6', 'MC', 'M2C'}
TARAMA = list(range(450, 1351, 50))
TOL = 2.0


def _e(nom, el):
    return nom.get(el, 0.0)


def ms_andrews(nom):
    """Andrews (1965) doğrusal bağıntısı — web arayüzündekiyle aynı."""
    return 539 - 423 * _e(nom, 'C') - 30.4 * _e(nom, 'Mn') - 17.7 * _e(nom, 'Ni') - 12.1 * _e(nom, 'Cr') - 7.5 * _e(nom, 'Mo')


def ms_eichelman_hull(nom):
    """Eichelman & Hull (1953), östenitik paslanmazlar için Ms (°C)."""
    return (1302 - 42 * _e(nom, 'Cr') - 61 * _e(nom, 'Ni') - 33 * _e(nom, 'Mn') - 28 * _e(nom, 'Si')
            - 1667 * (_e(nom, 'C') + _e(nom, 'N')))


def md30_angel(nom):
    """Angel (1954): %30 gerçek gerinimde %50 martenzit oluşan sıcaklık (°C). Oda sıcaklığına yakın/üstündeyse
    soğuk şekillendirmede deformasyon martenziti oluşur (manyetiklik, sertleşme)."""
    return (413 - 462 * (_e(nom, 'C') + _e(nom, 'N')) - 9.2 * _e(nom, 'Si') - 8.1 * _e(nom, 'Mn')
            - 13.7 * _e(nom, 'Cr') - 9.5 * _e(nom, 'Ni') - 18.5 * _e(nom, 'Mo'))


class _Tarayici:
    """Bir bileşim için sıcaklığa bağlı faz kümeleri; eşik sıcaklıklarını ikiye bölmeyle bulur."""

    def __init__(self, ps, bilesim):
        self.ps, self.bil, self.f = ps, bilesim, {}
        self.yok_sayilan = []
        for T in TARAMA:
            self.fazlar(T)

    def fazlar(self, T):
        T = round(T, 1)
        if T not in self.f:
            r = self.ps.hesapla(self.bil, T)
            self.f[T] = set(r['phases'])
            self.yok_sayilan = r['ignored_elements']
        return self.f[T]

    def esik(self, kosul, ilk=False):
        """
        Koşulun sağlanmamaktan sağlanmaya geçtiği sıcaklık (ısıtırken); yoksa None.
        ilk=False: son geçiş (üstünde taramanın sonuna kadar sağlanır). ilk=True: ilk geçiş (ör. Ae3; 13Cr çeliklerde
        daha yukarıda δ-ferrit yeniden çıkar, koşul sonra yine bozulur).
        """
        degerler = [(T, kosul(self.fazlar(T))) for T in TARAMA]
        gecisler = [j for j in range(len(degerler) - 1) if not degerler[j][1] and degerler[j + 1][1]]
        if degerler[0][1] or not gecisler or (not ilk and not degerler[-1][1]):
            return None
        i = gecisler[0] if ilk else gecisler[-1]
        a, b = degerler[i][0], degerler[i + 1][0]
        while b - a > TOL:
            m = (a + b) / 2
            a, b = (a, m) if kosul(self.fazlar(m)) else (m, b)
        return round((a + b) / 2)


def _calphad(ps, bilesim):
    t = _Tarayici(ps, bilesim)
    sigma_var = any('SG' in f for f in t.f.values())
    ae3 = t.esik(lambda f: 'A' not in f, ilk=True)
    # Ae3'ün üstünde ferrit yeniden çıkıyorsa (δ-ferrit) sertleştirme sıcaklığının üst sınırıdır
    delta = None
    if ae3 is not None:
        ust = [T for T in TARAMA if T > ae3 and 'A' in t.fazlar(T)]
        if ust:
            b = ust[0]
            a = max([ae3] + [T for T in TARAMA if ae3 < T < b])
            while b - a > TOL:
                m = (a + b) / 2
                a, b = (a, m) if 'A' in t.fazlar(m) else (m, b)
            delta = round((a + b) / 2)
    return {
        'Ae1': t.esik(lambda f: 'G' in f, ilk=True),
        'Ae3': ae3,
        'delta_ferrite': delta,
        'carbide_solvus': t.esik(lambda f: not (f & KARBURLER)),
        'sigma_solvus': t.esik(lambda f: 'SG' not in f) if sigma_var else None,
    }, t.yok_sayilan


def _hassaslasma_riski(nom):
    c, ti, nb = _e(nom, 'C'), _e(nom, 'Ti'), _e(nom, 'Nb')
    if ti >= 5 * c or nb >= 10 * c:
        return 'low', 'Ti/Nb ile kararlı kılınmış: karbon Cr yerine TiC/NbC olarak bağlanır.'
    if c <= 0.03:
        return 'low', 'Düşük karbonlu (L) kalite: kaynak ısıl etkisinde Cr karbür çökmesi sınırlı.'
    return 'high', ('C > %0,03 ve kararlı kılınmamış: 500–800 °C aralığında tutulursa (kaynak, yavaş soğuma) '
                    'tane sınırlarında Cr23C6 çöker, çevresi kromca fakirleşir → taneler arası korozyon.')


def mode_for(steel_class):
    return {'carbon_low_alloy': 'transformation', 'martensitic_stainless': 'transformation',
            'austenitic_stainless': 'solution_annealing', 'duplex_stainless': 'duplex',
            'ferritic_stainless': 'ferritic'}.get(steel_class, 'no_transformation')


def rejim(steel_class, nom, ps=None):
    """
    steel_class: steels.steel_class; nom: nominal bileşim {element: ağ.%} (Fe hariç).
    Dönüş: JSON'a hazır sözlük. Sıcaklıklar °C; None = bu bileşimde o geçiş yok / tarama aralığı dışında.
    """
    ps = ps or PointService()
    mod = mode_for(steel_class)
    T, yok = _calphad(ps, nom)
    out = {'mode': mod, 'steel_class': steel_class, 'calphad': T, 'ignored_elements': yok,
           'hide': [], 'notes': []}

    if mod == 'transformation':
        # ötektoid üstünde ferrit Ae1'de biter (Ae3 ≈ Ae1); sertleştirme Acm yerine bu sıcaklığın üstünden yapılır
        ae3 = T['Ae3']
        hiper = ae3 is not None and T['Ae1'] is not None and ae3 - T['Ae1'] < 10
        out.update({
            'Ms': round(ms_andrews(nom)), 'Ms_method': 'Andrews (1965)',
            'hypereutectoid': hiper,
            'hardening': [ae3 + 30, ae3 + 50] if ae3 else None,
            'hardening_basis': 'Ae1 + 30–50 °C (ötektoid üstü; Acm üstüne çıkılmaz)' if hiper else 'Ae3 + 30–50 °C',
        })
        if steel_class == 'martensitic_stainless' or (hiper and T['carbide_solvus'] and T['carbide_solvus'] - ae3 > 50):
            out['notes'].append(f'Karbürler {T["carbide_solvus"]} °C\'ye kadar tam çözünmüyor. Sertleştirme sıcaklığı bu '
                                'aralıkta yükseldikçe östenitin karbonu, martenzit sertliği ve kalıntı östenit artar; '
                                'pratikteki östenitleme sıcaklığı bu yüzden yukarıdaki kural değerinin üstünde olabilir.')
        if T['delta_ferrite']:
            out['notes'].append(f'{T["delta_ferrite"]} °C üstünde δ-ferrit oluşur: sertleştirme bunun altında yapılmalı '
                                '(δ-ferrit su vermede martenzite dönüşmez, sertliği ve tokluğu düşürür).')
        return out

    # A1/A3 yok: düşük sıcaklıktaki denge ferriti (ör. 321'de) kinetik olarak oluşmaz, gösterilmez
    T['Ae1'] = T['Ae3'] = T['delta_ferrite'] = None
    out['hide'] = ['hardening', 'A1', 'A3']
    if mod == 'solution_annealing':
        risk, aciklama = _hassaslasma_riski(nom)
        ms, md30 = ms_eichelman_hull(nom), md30_angel(nom)
        out.update({
            'solution_annealing': [1050, 1100], 'quench': 'Su veya hızlı hava (karbürler yeniden çökmeden 800–500 °C hızla geçilmeli)',
            'sensitization': {'range': [500, 800], 'risk': risk, 'reason': aciklama},
            'Ms': round(ms), 'Ms_method': 'Eichelman & Hull (1953)',
            'Ms_text': 'Oda sıcaklığının çok altında; soğutmayla martenzit oluşmaz.' if ms < -100 else None,
            'Md30': round(md30), 'Md30_method': 'Angel (1954)',
            'Md30_text': ('Soğuk şekillendirmede deformasyon martenziti beklenir (malzeme manyetikleşir, pekleşme artar).'
                          if md30 > 0 else 'Östenit oda sıcaklığında deformasyona karşı kararlı.'),
        })
        if T['carbide_solvus'] and T['carbide_solvus'] > 1050:
            out['notes'].append(f'Hesaplanan karbür çözünme sıcaklığı {T["carbide_solvus"]} °C: 1050 °C tavda karbürler '
                                'tam çözünmeyebilir, tav üst sınıra yakın yapılmalı.')
    elif mod == 'duplex':
        out.update({'solution_annealing': [1020, 1100],
                    'embrittlement_475': [400, 550],
                    'quench': 'Su (σ ve χ çökmesini önlemek için 1000–600 °C hızla geçilmeli)'})
    elif mod == 'ferritic':
        out.update({'annealing': [750, 850], 'embrittlement_475': [400, 550]})
        out['notes'].append('Ferritik paslanmaz su vermeyle sertleşmez; tane büyümesi geri döndürülemez, '
                            'yüksek sıcaklıkta uzun tutmaktan kaçının.')
    if T['sigma_solvus']:
        hiz = {'solution_annealing': 'Östenitte oluşumu yavaştır (yüzlerce saat); kaynak ve normal ısıl işlemde sorun '
                                     'çıkarmaz, ama bu aralıkta uzun süre çalışma tokluğu düşürür.',
               'duplex': 'Ferritten çok hızlı oluşur (dakikalar): kaynakta ve soğumada bu aralıkta beklenmemeli; '
                         'birkaç yüzde σ bile tokluğu ve korozyon direncini ciddi düşürür.'}
        out['notes'].append(f'Sigma fazı dengede {T["sigma_solvus"]} °C altında kararlı. '
                            + hiz.get(mod, 'Bu aralıkta uzun süre tutma tokluğu ve korozyon direncini düşürür.'))
    if mod == 'no_transformation':
        out['notes'].append('Bu sınıf için A1/A3, Ms ve Md30 bağıntıları geçerli değil; sadece CALPHAD denge sıcaklıkları verildi.')
    return out
