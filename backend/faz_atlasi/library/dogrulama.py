"""
Ölçümle doğrulama özeti: backend/validate_measured.py'nin raporundan (backend/data/dogrulama.json) arayüzün güven
etiketi için sınıf başına ölçülen Ac − hesaplanan Ae (yavaş ısıtma; ortalama, 1σ dağılım, ölçüm sayısı).
"""
import json
import os

RAPOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'dogrulama.json')


def ozet(yol=RAPOR):
    if not os.path.exists(yol):
        return None
    with open(yol, encoding='utf-8') as f:
        r = json.load(f)
    return {'kaynak': r['kaynak'], 'esik_Ks': r['yavas_esik_Ks'],
            'sinif': {s: {k: {x: v[k][x] for x in ('n', 'ortalama', 'sapma')} for k in ('Ae1', 'Ae3') if v.get(k)}
                      for s, v in r['sinif_yavas'].items()}}
