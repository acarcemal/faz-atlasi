"""Faz 3 testleri: çelik sınıfına göre ısıl işlem rejimi."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from faz_atlasi.calc.engine import TDB  # noqa: E402
from faz_atlasi.calc.isil_islem import md30_angel, mode_for, ms_eichelman_hull, rejim  # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.exists(TDB), reason='TDB yok')

AISI304 = {'C': 0.04, 'Si': 0.4, 'Mn': 1.2, 'Cr': 18.5, 'Ni': 9.25, 'N': 0.05}
AISI316L = {'C': 0.02, 'Si': 0.4, 'Mn': 1.2, 'Cr': 17.5, 'Ni': 11.5, 'Mo': 2.25, 'N': 0.05}
CRMO = {'C': 0.415, 'Mn': 0.75, 'Si': 0.25, 'Cr': 1.05, 'Mo': 0.225}
X20CR13 = {'C': 0.205, 'Si': 0.4, 'Mn': 0.6, 'Cr': 13.0}


@pytest.fixture(scope='module')
def ps():
    from faz_atlasi.calc.point import PointService
    return PointService()


def test_mod_secimi():
    assert mode_for('carbon_low_alloy') == mode_for('martensitic_stainless') == 'transformation'
    assert mode_for('austenitic_stainless') == 'solution_annealing'
    assert mode_for('duplex_stainless') == 'duplex'
    assert mode_for('fe_ni_alloy') == 'no_transformation'


def test_empirik_bagintilar():
    assert md30_angel(AISI304) == pytest.approx(16.6, abs=0.5)     # 304: oda sıcaklığına yakın → deformasyon martenziti
    assert md30_angel(AISI316L) < 0                                 # 316L: kararlı
    assert ms_eichelman_hull(AISI304) < -100


def test_islah_celigi_donusum_modu(ps):
    r = rejim('carbon_low_alloy', CRMO, ps)
    assert r['mode'] == 'transformation' and r['hide'] == []
    assert 715 <= r['calphad']['Ae1'] <= 740 and 760 <= r['calphad']['Ae3'] <= 790
    assert r['hardening'] == [r['calphad']['Ae3'] + 30, r['calphad']['Ae3'] + 50]
    assert r['Ms'] == 326


def test_martenzitik_paslanmaz_delta_ferrit(ps):
    r = rejim('martensitic_stainless', X20CR13, ps)
    T = r['calphad']
    assert T['Ae1'] < T['Ae3'] < T['carbide_solvus'] < T['delta_ferrite']
    assert any('δ-ferrit' in n for n in r['notes'])


def test_ostenitik_paslanmaz_cozeltiye_alma(ps):
    r = rejim('austenitic_stainless', AISI304, ps)
    assert r['mode'] == 'solution_annealing'
    assert set(r['hide']) >= {'hardening', 'A1', 'A3'}
    assert r['calphad']['Ae1'] is None and r['calphad']['Ae3'] is None
    assert r['solution_annealing'] == [1050, 1100]
    assert r['calphad']['carbide_solvus'] < 1050                   # tavda M23C6 tamamen çözünür
    assert r['sensitization']['risk'] == 'high' and r['sensitization']['range'] == [500, 800]
    assert r['Md30'] > 0 and r['Ms_text']
    assert r['ignored_elements'] == ['N']


def test_dusuk_karbon_ve_kararli_kalite_dusuk_risk(ps):
    assert rejim('austenitic_stainless', AISI316L, ps)['sensitization']['risk'] == 'low'
    ti = {**AISI304, 'C': 0.05, 'Ti': 0.4}
    assert rejim('austenitic_stainless', ti, ps)['sensitization']['risk'] == 'low'


def test_api_rejim(tmp_path_factory):
    from fastapi.testclient import TestClient
    from faz_atlasi.db import make_engine, make_session
    from faz_atlasi.library.build import build
    url = 'sqlite:///' + str(tmp_path_factory.mktemp('db') / 'test.db').replace('\\', '/')
    e = make_engine(url)
    build(e, make_session(e), log=lambda *_: None)
    os.environ['FAZ_DB_URL'], os.environ['FAZ_WARMUP'] = url, '0'
    from faz_atlasi.api.main import app
    with TestClient(app) as c:
        sid = c.get('/api/v1/steels', params={'q': '1.4301'}).json()['items'][0]['id']
        r = c.get(f'/api/v1/steels/{sid}/heat-treatment').json()
        assert r['standard_name'] == 'X5CrNi18-10' and r['mode'] == 'solution_annealing'
        r = c.post('/api/v1/heat-treatment', json={'composition': AISI304}).json()
        assert r['steel_class'] == 'austenitic_stainless' and r['steel_class_source'] == 'heuristic'
        assert c.post('/api/v1/heat-treatment', json={'composition': AISI304, 'steel_class': 'yok'}).status_code == 422
