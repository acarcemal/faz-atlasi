"""
Alaşım ailelerinin dikey kesitlerini sınır izleme ile hesaplayıp veritabanına (alloy_families.isopleth_boundaries) yazar.

  .venv/Scripts/python backend/trace_families.py Mn0.75_Si0.25_Cr1.05_Mo0.225   # tek aile
  .venv/Scripts/python backend/trace_families.py --eksik --islemci 4              # hesaplanmamış tüm aileler
  .venv/Scripts/python backend/trace_families.py --celik 42CrMo4                  # bir çeliğin ailesi

Bellek: işlem başına ~1 GB (çok bileşenli alaşımlarda daha fazla). Bilgisayar kullanılacaksa --islemci 2.
"""
import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faz_atlasi.calc.engine import get_engine  # noqa: E402
from faz_atlasi.calc.trace import isopleth  # noqa: E402
from faz_atlasi.db import AlloyFamily, Steel, make_engine, make_session  # noqa: E402
from faz_atlasi.library.search import search  # noqa: E402


def aile_girdisi(s, f, destekli):
    """Ailenin hesap bileşimi: TDB'de olmayan elementler çıkarılır; karbon referansı üyelerin ortalaması."""
    uyeler = s.query(Steel).filter_by(alloy_family_id=f.id).all()
    cs = [c.nominal().get('C', 0.2) for c in uyeler] or [0.2]
    C_ref = round(min(max(sum(cs) / len(cs), 0.05), 1.2), 3)
    bil = {e.upper(): v for e, v in f.base_elements.items() if e.upper() in destekli}
    yok = sorted(e for e in f.base_elements if e.upper() not in destekli)
    return bil, C_ref, yok


def main():
    p = argparse.ArgumentParser()
    p.add_argument('aileler', nargs='*')
    p.add_argument('--celik', action='append', default=[])
    p.add_argument('--eksik', action='store_true', help='kesiti olmayan tüm aileler')
    p.add_argument('--islemci', type=int, default=int(os.environ.get('FAZ_TRACE_PROCS', 4)))
    p.add_argument('--dT', type=float, default=5)
    a = p.parse_args()

    s = make_session(make_engine())
    hedef = list(a.aileler)
    for ad in a.celik:
        r = search(s, ad, limit=1)
        if not r:
            sys.exit(f'Çelik bulunamadı: {ad}')
        hedef.append(r[0]['steel'].alloy_family_id)
    if a.eksik:
        hedef += [f.id for f in s.query(AlloyFamily).filter(AlloyFamily.isopleth_boundaries.is_(None))]
    hedef = list(dict.fromkeys(hedef))
    destekli = get_engine().destekli
    print(f'{len(hedef)} aile, {a.islemci} işlem', flush=True)
    for i, fid in enumerate(hedef, 1):
        f = s.get(AlloyFamily, fid)
        if not f:
            print(f'  aile yok: {fid}')
            continue
        bil, C_ref, yok = aile_girdisi(s, f, destekli)
        t0 = time.time()
        sonuc = isopleth(bil, C_ref, dT=a.dT, islemci=a.islemci)
        sonuc['ignored_elements'] = yok
        f.isopleth_boundaries = sonuc
        f.calculated_at = datetime.utcnow()
        s.commit()
        print(f'[{i}/{len(hedef)}] {fid}: {time.time() - t0:.0f} s, {sonuc["meta"]["points"]} nokta'
              + (f' (hesap dışı: {", ".join(yok)})' if yok else ''), flush=True)


if __name__ == '__main__':
    main()
