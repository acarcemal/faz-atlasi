"""
Başka bir bilgisayarda hesaplanmış kesitleri bu veritabanına aktarır (trace_families.py --parca ile bölüşülmüş hesap).

  .venv/Scripts/python backend/merge_isopleths.py ikinci_bilgisayar.db

Sadece burada kesiti olmayan ve iki veritabanında bileşimi aynı olan ailelerin kesiti alınır; mevcut kesitlere
dokunulmaz. Kaynak veritabanı salt okunur açılır.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text  # noqa: E402

from faz_atlasi.db import AlloyFamily, make_engine, make_session  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    yol = os.path.abspath(sys.argv[1]).replace('\\', '/')
    kaynak = create_engine(f'sqlite:///file:{yol}?mode=ro&uri=true')
    with kaynak.connect() as k:
        satirlar = k.execute(text('SELECT id, base_elements, isopleth_boundaries, calculated_at FROM alloy_families '
                                  'WHERE isopleth_boundaries IS NOT NULL')).all()
    s = make_session(make_engine())
    alinan = atlanan = 0
    for fid, base, kesit, zaman in satirlar:
        f = s.get(AlloyFamily, fid)
        if f is None or f.isopleth_boundaries is not None:
            continue
        if f.base_elements != json.loads(base):
            atlanan += 1
            continue
        f.isopleth_boundaries = json.loads(kesit)
        f.calculated_at = datetime.fromisoformat(zaman) if zaman else datetime.utcnow()
        alinan += 1
    s.commit()
    print(f'{alinan} kesit aktarıldı' + (f', {atlanan} aile bileşimi farklı olduğu için atlandı' if atlanan else ''))


if __name__ == '__main__':
    main()
