"""
Doğrulama: hesaplanan denge sıcaklıklarını (Ae1, Ae3; calc/isil_islem._calphad) ölçülmüş dönüşüm sıcaklıklarıyla
(dilatometri, Ac1/Ac3) karşılaştırır. Ölçüm ısıtırken yapıldığı için Ac > Ae beklenir; ısıtma hızı düştükçe fark
küçülür. Bu yüzden sonuçlar ısıtma hızı aralıklarına göre ayrı verilir.

  .venv/Scripts/python backend/validate_measured.py backend/data/dogrulama/Austenite.data --islemci 3

Veri: MAP_DATA_AUSTENMAT, L. Gavard, H.K.D.H. Bhadeshia, D.J.C. MacKay, S. Suzuki, Mater. Sci. Technol. 12 (1996)
453-463 (University of Cambridge, Materials Algorithms Project). Sütunlar: sıra no, 21 element (ağ.%), Ac1 (°C),
Ac3 (°C), ısıtma hızı (K/s).
Karşılaştırma için Andrews (1965) doğrusal bağıntıları da hesaplanır (web arayüzünün empirik modeli).
Çıktı: backend/data/dogrulama.json (sınıf ve ısıtma hızı aralığına göre ortalama fark, sapma, en kötü örnekler).
"""
import argparse
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime
from multiprocessing import get_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faz_atlasi.calc import isil_islem  # noqa: E402
from faz_atlasi.calc.engine import get_engine  # noqa: E402
from faz_atlasi.library import classify  # noqa: E402

ELEMENTLER = ['C', 'Si', 'Mn', 'S', 'P', 'Cu', 'Ni', 'Cr', 'Mo', 'Nb', 'V', 'Ti', 'Al', 'B', 'W', 'As', 'Sn', 'Zr',
              'Co', 'N', 'O']
CIKTI = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'dogrulama.json')
KAYNAK = ('MAP_DATA_AUSTENMAT — L. Gavard, H.K.D.H. Bhadeshia, D.J.C. MacKay, S. Suzuki, '
          'Mater. Sci. Technol. 12 (1996) 453-463')
HIZ_ARALIKLARI = [(0, 0.1), (0.1, 1), (1, 10), (10, 1e9)]   # K/s


def oku(yol):
    """Başlık satırı atlanır. 43 satırda Ac3 ile ısıtma hızı bitişik yazılmış ('891.10.0000': 891,1 ve 0 mı,
    891 ve 10 K/s mi belirsiz); bunlar karşılaştırmaya alınmaz ve sayısı bildirilir."""
    satirlar, atlanan = [], 0
    with open(yol, encoding='latin-1') as f:
        for satir in f:
            p = satir.split()
            if not p or not p[0].isdigit():
                continue
            if len(p) != len(ELEMENTLER) + 4:
                atlanan += 1
                continue
            d = [float(x) for x in p]
            satirlar.append({'bil': dict(zip(ELEMENTLER, d[1:22])), 'Ac1': d[22], 'Ac3': d[23], 'hiz': d[24]})
    return satirlar, atlanan


def andrews(b):
    e = lambda el: b.get(el, 0.0)   # noqa: E731
    ac1 = 723 - 10.7 * e('Mn') - 16.9 * e('Ni') + 29.1 * e('Si') + 16.9 * e('Cr') + 290 * e('As') + 6.38 * e('W')
    ac3 = (910 - 203 * math.sqrt(e('C')) - 15.2 * e('Ni') + 44.7 * e('Si') + 104 * e('V') + 31.5 * e('Mo')
           + 13.1 * e('W') - 30 * e('Mn') - 11 * e('Cr') - 20 * e('Cu') + 700 * e('P') + 400 * e('Al')
           + 120 * e('As') + 400 * e('Ti'))
    return ac1, ac3


_ps = None


def _hesap(bil):
    global _ps
    if _ps is None:
        from faz_atlasi.calc.point import PointService
        _ps = PointService()
    nom = {e: v for e, v in bil.items() if v > 0}
    try:
        T, yok = isil_islem._calphad(_ps, nom)
        return T['Ae1'], T['Ae3'], yok, None
    except Exception as e:
        return None, None, [], f'{type(e).__name__}: {e}'


def ozet(farklar):
    if not farklar:
        return None
    return {'n': len(farklar), 'ortalama': round(statistics.mean(farklar), 1),
            'medyan': round(statistics.median(farklar), 1),
            'sapma': round(statistics.pstdev(farklar), 1),
            'ortalama_mutlak': round(statistics.mean(abs(x) for x in farklar), 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('veri')
    p.add_argument('--islemci', type=int, default=3)
    a = p.parse_args()
    olcum, okunamayan = oku(a.veri)
    # aynı bileşim farklı ısıtma hızlarında ölçülmüş: denge hesabı bileşim başına bir kez
    anahtar = lambda b: tuple(round(b[e], 4) for e in ELEMENTLER)   # noqa: E731
    bilesimler = {}
    for o in olcum:
        bilesimler.setdefault(anahtar(o['bil']), o['bil'])
    print(f'{len(olcum)} ölçüm ({okunamayan} satır okunamadı), {len(bilesimler)} farklı bileşim ({a.islemci} işlem)',
          flush=True)
    t0 = time.time()
    hesap = {}
    with get_context('spawn').Pool(a.islemci) as pool:
        for i, (k, r) in enumerate(zip(bilesimler, pool.imap(_hesap, bilesimler.values())), 1):
            hesap[k] = r
            if i % 25 == 0:
                print(f'  {i}/{len(bilesimler)} · {time.time() - t0:.0f} s', flush=True)

    satirlar, hatalar = [], 0
    for o in olcum:
        ae1, ae3, yok, hata = hesap[anahtar(o['bil'])]
        if hata:
            hatalar += 1
            continue
        an1, an3 = andrews(o['bil'])
        sinif = classify.heuristic({e: v for e, v in o['bil'].items() if v > 0})
        satirlar.append({'sinif': sinif, 'hiz': o['hiz'], 'bil': {e: v for e, v in o['bil'].items() if v > 0},
                         'Ac1': o['Ac1'], 'Ac3': o['Ac3'], 'Ae1': ae1, 'Ae3': ae3, 'Andrews1': round(an1, 1),
                         'Andrews3': round(an3, 1), 'hesap_disi': yok})

    def gruplar(satirlar, anahtar_fn):
        out = {}
        for s in satirlar:
            g = out.setdefault(anahtar_fn(s), {'Ae1': [], 'Ae3': [], 'Andrews1': [], 'Andrews3': []})
            if s['Ae1'] is not None and s['Ac1'] > 0:
                g['Ae1'].append(s['Ac1'] - s['Ae1'])
            if s['Ae3'] is not None and s['Ac3'] > 0:
                g['Ae3'].append(s['Ac3'] - s['Ae3'])
            if s['Ac1'] > 0:
                g['Andrews1'].append(s['Ac1'] - s['Andrews1'])
            if s['Ac3'] > 0:
                g['Andrews3'].append(s['Ac3'] - s['Andrews3'])
        return {k: {n: ozet(v) for n, v in g.items()} for k, g in out.items()}

    hiz_araligi = lambda s: next(f'{lo:g}-{hi:g} K/s' if hi < 1e9 else f'>{lo:g} K/s'   # noqa: E731
                                 for lo, hi in HIZ_ARALIKLARI if lo <= s['hiz'] < hi)
    # sınıf bazında sadece yavaş ısıtmalı ölçümler: dengeye en yakın olanlar
    esik = max(1.0, min(s['hiz'] for s in satirlar))
    yavas = [s for s in satirlar if s['hiz'] <= esik]
    rapor = {
        'kaynak': KAYNAK,
        'tarih': datetime.now().isoformat(timespec='seconds'),
        'tdb_sha': get_engine().tdb_ozet,
        'aciklama': ('fark = ölçülen Ac − hesaplanan Ae (°C). Ölçüm ısıtırken yapıldığından pozitif fark beklenir; '
                     'yavaş ısıtmada fark dengeye en yakındır.'),
        'olcum': len(olcum), 'okunamayan_satir': okunamayan, 'bilesim': len(bilesimler), 'hesaplanamayan': hatalar,
        'hiz_araligi': gruplar(satirlar, hiz_araligi),
        'yavas_esik_Ks': esik,
        'sinif_yavas': gruplar(yavas, lambda s: s['sinif']),
        'en_kotu': sorted(({'bil': s['bil'], 'hiz': s['hiz'], 'Ac3': s['Ac3'], 'Ae3': s['Ae3'],
                            'fark3': round(s['Ac3'] - s['Ae3'], 1)} for s in yavas if s['Ae3'] is not None),
                          key=lambda x: -abs(x['fark3']))[:10],
    }
    with open(CIKTI, 'w', encoding='utf-8') as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: rapor[k] for k in ('olcum', 'bilesim', 'hesaplanamayan', 'hiz_araligi', 'sinif_yavas')},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
