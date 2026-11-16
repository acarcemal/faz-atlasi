"""
Sınır izleme (boundary tracing) ile dikey kesit.

Tam ızgara (hesap/kesit_uret.py: 111 satır × 65+ karbon noktası) yerine her sıcaklık satırında:
  1. Seyrek karbon taraması (SEYREK, ~21 nokta) + bir önceki satırın sınırlarının iki yanı (ipucu noktaları)
  2. Faz kümesinin değiştiği her aralık, hepsi tek pycalphad çağrısında olacak şekilde ikiye bölünerek daraltılır
     (bisection) — aralık genişliği TOL(w) altına inene kadar. Aradan üçüncü bir küme çıkarsa aralık ikiye ayrılır.
Satırlar yukarıdan aşağı izlenir; sınırlar sıcaklıkla sürekli kaydığı için ipucu noktaları yeni satırdaki sınırı
çoğunlukla ilk adımda yakalar. Paralel çalışmada sıcaklık aralığı parçalara bölünür, her parça kendi zincirini izler.

Bileşim gösterimi kesit_uret.py ile aynıdır: alaşım elementlerinin mol kesri, ailenin referans karbonunda sabit.
Çıktı satırları web arayüzünün kesit biçimiyle uyumludur: {'T', 'r': [{'p': [fazlar], 'x': [C_baş, C_son]}]}.
"""
import os
import time
from multiprocessing import get_context

import numpy as np

from .engine import agirlik_to_mol, fazlar_icin, get_engine, sira, wC_to_xC

SEYREK = [0.002, 0.006, 0.01, 0.02, 0.035, 0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.45, 0.55, 0.65, 0.77, 0.9,
          1.05, 1.2, 1.4, 1.6, 1.8]


def tol(w):
    """Sınırın kabul edilen belirsizliği (ağ.% C): düşük karbonda ferrit çözünürlüğü için ince, yüksekte kaba."""
    return max(0.002, 0.008 * w)


def _alas_mol(bilesim, C_ref):
    x = agirlik_to_mol({**bilesim, 'C': C_ref})
    return {e: v for e, v in x.items() if e not in ('C', 'FE')}


def _anahtar(r):
    return None if r is None else sira(r)


def _kosular(gecerli):
    """Aynı faz kümesine sahip ardışık nokta grupları: [[(w, k), ...], ...]"""
    out = []
    for w, k in gecerli:
        if out and out[-1][-1][1] == k:
            out[-1].append((w, k))
        else:
            out.append([(w, k)])
    return out


def satir_izle(motor, xa, fazlar, T, ipucu=(), C_max=1.8):
    """
    Tek sıcaklık satırı. Tarama ve daraltma hızlı ızgarayla (HIZLI_PDENS) yapılır; sonra her bölgenin ortasındaki
    bir nokta varsayılan ızgarayla doğrulanır. Doğrulama farklı küme verirse o bölgenin bütün noktaları varsayılan
    ızgarayla yeniden hesaplanır ve daraltma tekrarlanır.
    Dönüş: (bölgeler, sınırlar, hesaplanan nokta sayısı).
    """
    nokta, kesin = {}, set()
    sayac = [0]

    def hesapla(ws, dogrula=False):
        ws = sorted({round(float(w), 5) for w in ws if 0 < w <= C_max}
                    - (kesin if dogrula else set(nokta)))
        if ws:
            pd = None if dogrula else motor.HIZLI_PDENS
            for w, r in zip(ws, motor.coz_saglam(xa, [wC_to_xC(w, xa) for w in ws], T, fazlar, pd)):
                eski = nokta.get(w)
                nokta[w] = _anahtar(r)
                if dogrula:
                    kesin.add(w)
                    if eski is not None and eski != nokta[w]:
                        sayac[0] += 1
        return len(ws)

    hesapla([w for w in SEYREK if w <= C_max] + [C_max] + list(ipucu))
    for _ in range(60):
        gecerli = sorted((w, k) for w, k in nokta.items() if k is not None)
        araliklar = [(a, b) for (a, ka), (b, kb) in zip(gecerli, gecerli[1:]) if ka != kb and b - a > tol(b)]
        yeni = []
        for a, b in araliklar:
            orta = round((a + b) / 2, 5)
            # orta nokta daha önce denenip çözülemediyse çeyrek noktalar denenir
            yeni += [a + (b - a) / 4, b - (b - a) / 4] if orta in nokta else [orta]
        if araliklar and hesapla(yeni):
            continue
        # doğrulama: hiç kesin noktası olmayan bölgelerin ortanca noktası
        kosular = [k for k in _kosular(gecerli) if not any(w in kesin for w, _ in k)]
        if not kosular:
            break
        once = sayac[0]
        hesapla([k[len(k) // 2][0] for k in kosular], dogrula=True)
        if sayac[0] > once:
            # yanlış çıkan bölgelerin tüm noktaları kesin ızgarayla
            supheli = [w for k in kosular for w, _ in k if nokta[k[len(k) // 2][0]] != k[0][1]]
            hesapla(supheli, dogrula=True)

    gecerli = sorted((w, k) for w, k in nokta.items() if k is not None)
    bolgeler, sinirlar = [], []
    for i, (w, k) in enumerate(gecerli):
        if bolgeler and bolgeler[-1]['p'] == list(k):
            continue
        s = 0.0 if i == 0 else round(0.5 * (gecerli[i - 1][0] + w), 4)
        if bolgeler:
            bolgeler[-1]['x'][1] = s
            sinirlar.append({'C': s, 'sol': bolgeler[-1]['p'], 'sag': list(k)})
        bolgeler.append({'p': list(k), 'x': [s, None]})
    bolgeler[-1]['x'][1] = C_max
    return bolgeler, sinirlar, len(nokta)


def _ipucu(sinirlar):
    out = []
    for s in sinirlar:
        d = max(0.004, 0.04 * s['C'])
        out += [s['C'] - d, s['C'] + d]
    return out


def _parca(args):
    bilesim, C_ref, Ts, C_max = args
    motor = get_engine()
    xa = _alas_mol(bilesim, C_ref)
    fazlar = fazlar_icin(bilesim)
    satirlar, ipucu, n = [], (), 0
    for T in Ts:
        b, s, k = satir_izle(motor, xa, fazlar, T, ipucu, C_max)
        satirlar.append({'T': T, 'r': b, 's': s})
        ipucu, n = _ipucu(s), n + k
    return satirlar, n


def cizgiler(satirlar):
    """Ardışık satırlardaki aynı tür sınırları (sol/sağ faz kümesi aynı, C'si en yakın) çoklu çizgilere bağlar."""
    acik, biten = [], []
    for satir in satirlar:
        yeni = []
        for s in satir['s']:
            tur = (tuple(s['sol']), tuple(s['sag']))
            aday = [c for c in acik if c['tur'] == tur and c not in yeni]
            c = min(aday, key=lambda c: abs(c['pts'][-1][0] - s['C']), default=None)
            if c is None or abs(c['pts'][-1][0] - s['C']) > max(0.1, 0.3 * s['C']):
                c = {'tur': tur, 'pts': []}
            c['pts'].append([s['C'], satir['T']])
            yeni.append(c)
        biten += [c for c in acik if c not in yeni]
        acik = yeni
    biten += acik
    return [{'between': [list(c['tur'][0]), list(c['tur'][1])], 'pts': c['pts']} for c in biten]


def isopleth(bilesim, C_ref, T_min=550, T_max=1100, dT=5, C_max=1.8, islemci=None):
    """
    bilesim: alaşım elementleri ağ.% (büyük harf, C hariç), C_ref: alaşım mol kesirlerinin sabitlendiği karbon.
    Dönüş: JSON'a hazır sözlük (alloy_families.isopleth_boundaries).
    """
    t0 = time.time()
    Ts = [float(T) for T in np.arange(T_max, T_min - 0.01, -dT)]
    islemci = islemci or int(os.environ.get('FAZ_TRACE_PROCS', 1))
    if islemci > 1:
        parcalar = [list(p) for p in np.array_split(Ts, islemci) if len(p)]
        with get_context('spawn').Pool(len(parcalar)) as pool:
            sonuc = pool.map(_parca, [(bilesim, C_ref, [float(T) for T in p], C_max) for p in parcalar])
        satirlar = [s for p, _ in sonuc for s in p]
        n = sum(k for _, k in sonuc)
    else:
        satirlar, n = _parca((bilesim, C_ref, Ts, C_max))
    satirlar.sort(key=lambda s: s['T'])
    return {
        'composition': {e.capitalize(): v for e, v in bilesim.items()},
        'C_ref': C_ref,
        'x_alloy': _alas_mol(bilesim, C_ref),
        'T': [T_min, T_max, dT], 'C_max': C_max,
        'rows': [{'T': s['T'], 'r': s['r']} for s in satirlar],
        'lines': cizgiler(satirlar),
        'phases_considered': fazlar_icin(bilesim),
        'meta': {'method': 'boundary tracing (row bisection)', 'points': n, 'seconds': round(time.time() - t0, 1),
                 'model': 'MatCalc mc_fe v2.062 (ODbL) + pycalphad'},
    }
