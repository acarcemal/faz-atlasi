"""Faz 1 testleri: veritabanı kurulumu, tek çelik / çoklu norm, arama, aileler, paslanmaz sınıfları.

  .venv/Scripts/python -m pytest backend/tests -q
"""
import collections
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from faz_atlasi.db import AlloyFamily, Steel, SteelDesignation, make_engine, make_session  # noqa: E402
from faz_atlasi.library import families  # noqa: E402
from faz_atlasi.library.build import build  # noqa: E402
from faz_atlasi.library.designations import normalize, parse_dataset_name  # noqa: E402
from faz_atlasi.library.search import designations_by_system, search  # noqa: E402


@pytest.fixture(scope='module')
def s():
    engine = make_engine('sqlite:///:memory:')
    session = make_session(engine)
    build(engine, session, log=lambda *_: None)
    return session


def celik(s, ad):
    return s.query(Steel).filter_by(standard_name=ad).one()


def ilk(s, q, **kw):
    return search(s, q, **kw)[0]['steel'].standard_name


@pytest.mark.parametrize('q', ['42CrMo4', '42crmo4', '1.7225', 'W.Nr. 1.7225', '4140', 'AISI 4140', 'SAE 4140',
                               'SCM440', 'JIS SCM 440', 'G41400', 'UNS G41400'])
def test_ayni_celige_her_normla_ulasilir(s, q):
    assert ilk(s, q) == '42CrMo4'


@pytest.mark.parametrize('q,ad', [('304', 'X5CrNi18-10'), ('1.4301', 'X5CrNi18-10'), ('SUS304', 'X5CrNi18-10'),
                                  ('316L', 'X2CrNiMo17-12-2'), ('1.4021', 'X20Cr13'), ('AISI 420', 'X20Cr13'),
                                  ('1.4034', 'X46Cr13'), ('440B', 'X90CrMoV18'), ('12Х18Н10Т', '12X18N10T')])
def test_paslanmaz_ve_gost_arama(s, q, ad):
    assert ilk(s, q) == ad


def test_mukerrer_kayit_yok(s):
    # aynı norm adı (kesin, kalite düzeyinde) iki farklı çeliğe ait olamaz
    sayac = collections.Counter((d.system, d.code_norm) for d in s.query(SteelDesignation)
                                .filter_by(approx=False, scope='grade'))
    assert [k for k, n in sayac.items() if n > 1] == []


def test_veri_seti_kaydi_mevcut_celige_baglanir(s):
    c = celik(s, '42CrMo4')
    assert {x.source_ref for x in c.sources} >= {'42CrMo4', 'AISI 4140 Steel'}
    assert s.query(Steel).filter_by(standard_name='AISI 4140 Steel').count() == 0
    # bileşim standart aralıktan kalır (veri setinin tek bileşimi üzerine yazılmaz)
    cr = next(x for x in c.composition if x.element == 'Cr')
    assert (cr.min_val, cr.max_val) == (0.90, 1.20)
    # UNS üzerinden gelen ticari ad da AISI 4340'a bağlanır
    assert 'TRADE' in designations_by_system(celik(s, 'AISI 4340'))


def test_yaklasik_karsilik_birlestirmez(s):
    # JIS S45C veri setinde ayrı çelik; C45E'de ise ≈S45C olarak durur
    sonuc = [(r['steel'].standard_name, r['matched'].approx) for r in search(s, 'S45C')]
    assert ('JIS S45C Steel', False) in sonuc and ('C45E', True) in sonuc


def test_norm_bazli_listeleme(s):
    jis = search(s, '', system='JIS', limit=500)
    assert jis and all(r['matched'].system == 'JIS' for r in jis)
    assert any(r['display_name'] == 'SUS304' for r in jis)


def test_crmo_ailesi_ortak(s):
    aile = {celik(s, a).alloy_family_id for a in ('25CrMo4', '34CrMo4', '42CrMo4', '50CrMo4')}
    assert len(aile) == 1


def test_her_celigin_ailesi_var_ve_tutarli(s):
    assert s.query(Steel).filter(Steel.alloy_family_id.is_(None)).count() == 0
    for c in s.query(Steel):
        assert families.close(families.alloy_part(c.nominal()), c.family.base_elements), c.standard_name
    assert s.query(AlloyFamily).count() < s.query(Steel).count()


@pytest.mark.parametrize('ad,sinif', [('X20Cr13', 'martensitic_stainless'), ('X46Cr13', 'martensitic_stainless'),
                                      ('X90CrMoV18', 'martensitic_stainless'), ('X5CrNi18-10', 'austenitic_stainless'),
                                      ('X5CrNiMo17-12-2', 'austenitic_stainless'), ('X6Cr17', 'ferritic_stainless'),
                                      ('X2CrNiMoN22-5-3', 'duplex_stainless'), ('42CrMo4', 'carbon_low_alloy'),
                                      ('12X18N10T', 'austenitic_stainless'), ('Cast Stainless Steel CF8', 'austenitic_stainless')])
def test_mikroyapi_sinifi(s, ad, sinif):
    assert celik(s, ad).steel_class == sinif


def test_ad_ayristirma():
    assert parse_dataset_name('AISI E4340 H Steel') == [('AISI', 'E4340H', 'grade')]
    assert parse_dataset_name('ASTM A387 Alloy Steel') == [('ASTM', 'A387', 'specification')]
    assert parse_dataset_name('ASTM A209 T1 Alloy Steel') == [('ASTM', 'A209 T1', 'grade')]
    assert parse_dataset_name('AK Steel ASTM A 424 Type II') == [('ASTM', 'A424 Type II', 'grade')]
    assert parse_dataset_name('Cast Stainless Steel CF8M') == [('ACI', 'CF8M', 'grade')]
    assert parse_dataset_name('BS 970/1(83) 070M55 Nonresulfurized Carbon Steel') == [('BS', '070M55', 'grade')]
    assert normalize('36X18N25C2', 'GOST') == normalize('36Х18Н25С2', 'GOST') == normalize('36X18N25S2', 'GOST')
