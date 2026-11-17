"""Sunucusuz site için statik aktarım (backend/export_static.py): dosya biçimi ve içerik."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import export_static  # noqa: E402
from faz_atlasi.db import AlloyFamily, Steel, ensure_schema, make_engine, make_session  # noqa: E402
from faz_atlasi.library.alt_aile import celik_anahtari  # noqa: E402
from faz_atlasi.library.build import build  # noqa: E402


def js_json(yol, on):
    s = open(yol, encoding='utf-8').read()
    assert s.startswith(on), s[:80]
    return json.loads(s[len(on):s.rindex(')' if on.endswith(',') else ';')])


def test_aktarim(tmp_path, monkeypatch):
    engine = make_engine('sqlite:///:memory:')
    ensure_schema(engine)
    s = make_session(engine)
    build(engine, s, log=lambda *_: None, alt_aileler=None)
    c = s.query(Steel).filter_by(standard_name='42CrMo4').one()
    f = s.get(AlloyFamily, c.alloy_family_id)
    f.isopleth_boundaries = {'composition': {'Mn': 0.75}, 'C_ref': 0.4, 'T': [550, 1100, 5], 'C_max': 1.8,
                             'rows': [{'T': 550.0, 'r': [{'p': ['A', 'C'], 'x': [0, 1.8]}]}], 'lines': [{'pts': []}],
                             'ignored_elements': []}
    s.flush()
    monkeypatch.setattr(export_static, 'WEB', str(tmp_path))
    rejim = {'mode': 'transformation', 'calphad': {'Ae1': 727}}
    export_static.aktar(s, {celik_anahtari(c): {'rejim': rejim}})

    aile = js_json(tmp_path / 'aile' / f'{f.id}.js', f'AILE_YUKLE({json.dumps(f.id)},')
    assert aile['rows'][0]['r'][0]['p'] == ['A', 'C'] and 'lines' not in aile   # arayüzün kullanmadığı alan çıkar
    k = js_json(tmp_path / 'kutuphane' / 'celikler2.js',
                '// backend/export_static.py ile üretildi — elle düzenleme yapmayın\nwindow.KUTUPHANE_V2=')
    assert k['meta']['celik'] == s.query(Steel).count() == len(k['celikler'])
    assert k['aileler'][f.id]['kesit'] and not all(a['kesit'] for a in k['aileler'].values())
    x = next(y for y in k['celikler'] if y['ad'] == '42CrMo4')
    assert ['WNR', '1.7225', 0, '17225'] in x['adlar'] and x['aile'] == f.id and x['rejim'] == rejim
    assert x['bil'][0][0] == 'C' and x['eksik'] == []
