"""
Çelik veritabanını kurar.

  .venv/Scripts/python backend/build_db.py                       # backend/data/faz_atlasi.db (SQLite)
  FAZ_DB_URL=postgresql+psycopg://... .venv/Scripts/python backend/build_db.py
  .venv/Scripts/python backend/build_db.py --esdeger lisansli_esdegerler.csv   # ek norm eşleştirmeleri
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faz_atlasi.db import AlloyFamily, Steel, make_engine, make_session  # noqa: E402
from faz_atlasi.library.build import build  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', help='SQLAlchemy URL (varsayılan FAZ_DB_URL ya da backend/data/faz_atlasi.db)')
    p.add_argument('--esdeger', action='append', default=[], help='ek eşdeğer CSV dosyası (esdegerler.csv biçiminde)')
    a = p.parse_args()
    engine = make_engine(a.db)
    s = make_session(engine)
    print(f'Veritabanı: {engine.url.render_as_string(hide_password=True)}')
    k = build(engine, s, a.esdeger)

    celikler = s.query(Steel).all()
    print(f'\nToplam {len(celikler)} çelik, {s.query(AlloyFamily).count()} alaşım ailesi')
    print('Sınıflar:', dict(collections.Counter(c.steel_class for c in celikler).most_common()))
    uye = collections.Counter(c.alloy_family_id for c in celikler)
    print('En kalabalık aileler:')
    for fid, n in uye.most_common(8):
        ornek = ', '.join(c.standard_name for c in celikler if c.alloy_family_id == fid)[:90]
        print(f'  {n:3d}  {fid:45s} {ornek}')
    if k.uyari:
        print(f'\n{len(k.uyari)} uyarı:')
        for u in k.uyari:
            print('  ' + u)


if __name__ == '__main__':
    main()
