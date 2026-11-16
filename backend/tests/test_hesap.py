"""Faz 2 testleri: pycalphad motoru, tek nokta denge, sınır izleme, REST API.

TDB (hesap/tdb/mc_fe_pycalphad.tdb) yoksa atlanır. İlk test TDB'yi yükleyip modelleri derlediği için ~20 s sürer.
"""
import json
import os
import statistics
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from faz_atlasi.calc.engine import TDB, agirlik_to_mol, fazlar_icin, get_engine  # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.exists(TDB), reason='TDB yok')

KOK = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CRMO = {'C': 0.42, 'Mn': 0.75, 'Si': 0.25, 'Cr': 1.05, 'Mo': 0.225}
AISI304 = {'C': 0.04, 'Si': 0.4, 'Mn': 1.2, 'Cr': 18.5, 'Ni': 9.25, 'N': 0.05}


@pytest.fixture(scope='module')
def nokta():
    from faz_atlasi.calc.point import PointService
    return PointService()


def test_desteklenen_elementler():
    assert {'C', 'MN', 'SI', 'CR', 'NI', 'MO', 'V', 'W', 'CU'} <= get_engine().destekli


def test_42crmo4_iki_fazli_bolge(nokta):
    # hesap/kesit_uret.py ile aynı sonuç (760 °C'de östenit + ferrit)
    r = nokta.hesapla(CRMO, 760)
    assert set(r['phases']) == {'G', 'A'}
    assert r['phases']['G'] == pytest.approx(0.881, abs=0.005)
    assert r['carbon_in_phases']['G'] == pytest.approx(0.475, abs=0.01)
    assert nokta.hesapla(CRMO, 900)['phases'] == {'G': 1.0}


def test_onbellek(nokta):
    nokta.hesapla(CRMO, 731.5)
    r = nokta.hesapla(CRMO, 731.5)
    assert r['cached'] and r['elapsed_ms'] < 5


def test_304_cozeltiye_alma_ve_azot_bildirimi(nokta):
    r = nokta.hesapla(AISI304, 1075)
    assert r['phases'] == {'G': 1.0}
    assert r['ignored_elements'] == ['N']
    assert 'SIGMA' in r['phases_considered']
    assert 'K23' in nokta.hesapla(AISI304, 650)['phases']   # hassaslaşma aralığında M23C6


def test_sicak_tek_nokta_suresi(nokta):
    sureler = [nokta.hesapla(CRMO, 600 + 11.3 * i)['elapsed_ms'] for i in range(15)]
    medyan = statistics.median(sureler)
    print(f'\n42CrMo4 tek nokta (sıcak, önbelleksiz): medyan {medyan:.0f} ms')
    assert medyan < 250   # makineye bağlı; ölçüm README'de raporlanır


def test_hizli_izgara_tuzagi():
    """HIZLI_PDENS bu noktada yanlış küme verir; tek nokta hesabı (varsayılan ızgara) doğruyu vermeli."""
    m = get_engine()
    w = {'MN': 0.75, 'SI': 0.25, 'CR': 1.05, 'MO': 0.225}
    x = agirlik_to_mol({**w, 'C': 0.25})
    xa = {e: v for e, v in x.items() if e not in ('C', 'FE')}
    dogru = m.coz(xa, [x['C']], 550, fazlar_icin(w))[0]
    assert set(dogru) == {'A', 'C', 'K7'}


def test_sinir_izleme_yanlis_bolgeyi_dogrular():
    from faz_atlasi.calc.trace import _alas_mol, satir_izle
    w = {'MN': 0.75, 'SI': 0.25, 'CR': 1.05, 'MO': 0.225}
    bolgeler, _, _ = satir_izle(get_engine(), _alas_mol(w, 0.375), fazlar_icin(w), 550.0)
    dizi = [b['p'] for b in bolgeler]
    i = dizi.index(['A', 'K7'])
    assert dizi[i + 1] == ['A', 'C', 'K7']   # arada sahte A+C+K23 bölgesi yok


def test_sinir_izleme_eski_izgarayla_uyumlu():
    from faz_atlasi.calc.trace import isopleth
    anahtar = 'Mn0.75_Si0.25_Cr1.05_Mo0.225'
    yol = os.path.join(KOK, 'web', 'veri', 'kesit', anahtar + '.js')
    if not os.path.exists(yol):
        pytest.skip('eski kesit dosyası yok')
    ham = open(yol, encoding='utf-8').read()
    eski = json.loads(ham[ham.index(',') + 1:ham.rindex(')')])
    bil = {e.upper(): v for e, v in eski['bilesim'].items() if e != 'C'}
    r = isopleth(bil, eski['bilesim']['C'], T_min=700, T_max=800, dT=25, islemci=1)
    yeni = {row['T']: row['r'] for row in r['rows']}
    for row in eski['rows']:
        if row['T'] not in yeni:
            continue
        a, b = row['r'], yeni[row['T']]
        assert [x['p'] for x in a] == [x['p'] for x in b], row['T']
        for x, y in zip(a[1:], b[1:]):
            # eski ızgaranın çözünürlüğü ~0,004; izlemenin toleransı 0,008·C
            assert abs(x['x'][0] - y['x'][0]) <= max(0.006, 0.02 * x['x'][0]), (row['T'], x, y)


@pytest.fixture(scope='module')
def istemci(tmp_path_factory):
    from fastapi.testclient import TestClient
    from faz_atlasi.db import make_engine, make_session
    from faz_atlasi.library.build import build
    url = 'sqlite:///' + str(tmp_path_factory.mktemp('db') / 'test.db').replace('\\', '/')
    e = make_engine(url)
    build(e, make_session(e), log=lambda *_: None)
    os.environ['FAZ_DB_URL'] = url
    from faz_atlasi.api.main import app
    with TestClient(app) as c:
        yield c


def test_api_celik_arama_ve_detay(istemci):
    r = istemci.get('/api/v1/steels', params={'q': 'SCM440'}).json()
    assert r['items'][0]['standard_name'] == '42CrMo4'
    d = istemci.get(f'/api/v1/steels/{r["items"][0]["id"]}').json()
    assert d['designations']['WNR'][0]['code'] == '1.7225'
    assert {c['element'] for c in d['composition']} >= {'C', 'Cr', 'Mo'}
    jis = istemci.get('/api/v1/steels', params={'system': 'JIS', 'limit': 3}).json()
    assert all(x['matched']['system'] == 'JIS' for x in jis['items'])
    assert istemci.get('/api/v1/steels/999999').status_code == 404


def test_api_tek_nokta(istemci):
    istek = {'composition': CRMO, 'T': 760}
    r = istemci.post('/api/v1/equilibrium/point', json=istek)
    assert r.status_code == 200 and set(r.json()['phases']) == {'G', 'A'}
    r2 = istemci.post('/api/v1/equilibrium/point', json=istek).json()
    assert r2['cached']
    assert istemci.post('/api/v1/equilibrium/point', json={'composition': {'C': 0.4, 'Xx': 1}, 'T': 700}).status_code == 422
    assert istemci.post('/api/v1/equilibrium/point', json={'composition': {'Cr': 1}, 'T': 700}).status_code == 422


def test_api_aile_ve_kesit(istemci):
    f = istemci.get('/api/v1/families/Mn0.75_Si0.25_Cr1.05_Mo0.225').json()
    assert f['steel_count'] >= 4
    assert istemci.get('/api/v1/isopleth/Mn0.75_Si0.25_Cr1.05_Mo0.225').status_code == 404   # henüz hesaplanmadı
