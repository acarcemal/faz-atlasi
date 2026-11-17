"""Alt aileler: ölçülen sapmaya göre aileleri bölme (library/alt_aile.py) ve sapma karşılaştırması (calc/sapma.py).

Ölçüm yerine sahte bir sapma fonksiyonu kullanılır (Si farkı × 100 °C); sadece sapma.olc testi TDB ister.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from faz_atlasi.calc import sapma  # noqa: E402
from faz_atlasi.calc.engine import TDB  # noqa: E402
from faz_atlasi.db import AlloyFamily, Steel, SteelFamilyFit, make_engine, make_session  # noqa: E402
from faz_atlasi.library import alt_aile  # noqa: E402
from faz_atlasi.library.build import build  # noqa: E402

AILE = {'Mn': 0.75, 'Si': 0.25}


def sahte_olc(nom, alasim):
    d = round(100 * (nom.get('Si', 0) - alasim.get('Si', 0)))
    return sapma.karsilastir({'Ae3': 800 + d}, {'Ae3': 800})


def test_karsilastir_esik_ve_yapi_farki():
    assert sapma.karsilastir({'Ae1': 727, 'Ae3': 790}, {'Ae1': 725, 'Ae3': 785})['within']
    o = sapma.karsilastir({'Ae1': 727, 'Ae3': 796}, {'Ae1': 725, 'Ae3': 785})
    assert not o['within'] and o['max_abs_delta'] == 11
    # geçişin birinde olup ötekinde olmaması tolerans dışıdır
    o = sapma.karsilastir({'Ae1': None, 'Ae3': 790}, {'Ae1': 712, 'Ae3': 790})
    assert not o['within'] and o['mismatch'][0]['key'] == 'Ae1'


def test_ayir():
    uyeler = [
        ('a', {'C': 0.4, 'Mn': 0.75, 'Si': 0.25}),   # ailede kalır
        ('b', {'C': 0.2, 'Mn': 0.75, 'Si': 0.0}),    # 25 °C sapar; yakın mevcut aile X'e uyar
        ('e', {'C': 0.3, 'Mn': 0.75, 'Si': 0.55}),   # 30 °C sapar; X uzak -> yeni alt aile
        ('f', {'C': 0.3, 'Mn': 0.75, 'Si': 0.57}),   # e'nin alt ailesine uyar
    ]
    adaylar = [('X', {'Mn': 0.75, 'Si': 0.05}), ('Mn0.75_Si0.25', AILE)]
    atama, olcumler, yeni = alt_aile.ayir('Mn0.75_Si0.25', AILE, uyeler, sahte_olc, adaylar,
                                          kullanilan={'Mn0.75_Si0.55'})
    assert atama['a'] == 'Mn0.75_Si0.25'
    assert atama['b'] == 'X'
    assert atama['e'] == atama['f'] == 'Mn0.75_Si0.55~2'      # kimlik çakışması çözülür
    assert yeni == {'Mn0.75_Si0.55~2': ('e', {'Mn': 0.75, 'Si': 0.55}, 'Mn0.75_Si0.25')}
    assert all(o['within'] for o in olcumler.values())


@pytest.fixture(scope='module')
def s():
    engine = make_engine('sqlite:///:memory:')
    session = make_session(engine)
    build(engine, session, log=lambda *_: None, alt_aileler=None)
    return session


def test_uygula_ve_bos_aile(s):
    st = s.query(Steel).filter_by(standard_name='50CrMo4').one()
    ust = st.family
    fit = sapma.karsilastir({'Ae3': 770}, {'Ae3': 760})
    alt = alt_aile.alasim(st.nominal())
    kayit = {
        'families': {ust.id: {'base': ust.base_elements, 'done': True}},
        'subfamilies': {'Mn0.65_Si0.25_Cr1.05_Mo0.225~t': {'parent': ust.id, 'base': alt,
                                                          'founder': alt_aile.celik_anahtari(st)}},
        'steels': {alt_aile.celik_anahtari(st): {'family': 'Mn0.65_Si0.25_Cr1.05_Mo0.225~t', 'parent': ust.id,
                                                  'family_base': alt, 'fit': fit},
                   # aile yapısı değişmiş (üst aile bileşimi farklı) -> atlanır
                   'faz_atlasi_lib|42CrMo4': {'family': 'yok', 'parent': 'baska', 'family_base': {}, 'fit': fit}},
    }
    tasinan, eklenen, atlanan = alt_aile.uygula(s, kayit, log=lambda *_: None)
    assert (tasinan, eklenen, atlanan) == (1, 1, 1)
    assert st.alloy_family_id == 'Mn0.65_Si0.25_Cr1.05_Mo0.225~t'
    assert s.get(AlloyFamily, st.alloy_family_id).parent_id == ust.id
    assert s.get(SteelFamilyFit, st.id).max_abs_delta == 10
    # üst ailede başka çelikler kaldığı için silinmez; üyesiz ve kesitsiz aile silinir
    s.add(AlloyFamily(id='bos', base_elements={'Mn': 9}))
    s.flush()
    assert alt_aile.bos_aileleri_sil(s) == 1 and s.get(AlloyFamily, ust.id) is not None


@pytest.mark.skipif(not os.path.exists(TDB), reason='TDB yok')
def test_olc_gercek_celik():
    from faz_atlasi.calc.point import PointService
    nom = {'C': 0.5, 'Mn': 0.65, 'Si': 0.25, 'Cr': 1.05, 'Mo': 0.225}            # 50CrMo4
    o = sapma.olc(PointService(), nom, {'Mn': 0.75, 'Si': 0.25, 'Cr': 1.05, 'Mo': 0.225})
    assert o['within'] and o['max_abs_delta'] <= 5 and {p['key'] for p in o['pairs']} >= {'Ae1', 'Ae3'}
