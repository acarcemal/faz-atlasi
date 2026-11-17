"""
Alt aileler: her çeliği ailesinin kesitine karşı CALPHAD ile ölçer, farkı ESIK'i (5 °C) aşanları alt aileye ayırır
(faz_atlasi/library/alt_aile.py, faz_atlasi/calc/sapma.py).

  .venv/Scripts/python backend/split_families.py               # ölç -> backend/data/alt_aileler.json
  .venv/Scripts/python backend/split_families.py --uygula      # ölçülenleri veritabanına işle
  .venv/Scripts/python backend/split_families.py --aile Mn0.75_Si0.25 --islemci 2

Ölçüm veritabanına yazmaz (çalışan bir trace_families.py ile çakışmasın). --uygula yazar: alt aileleri kurar,
çelikleri taşır, ölçümleri steel_family_fit tablosuna koyar, üyesi kalmamış ve kesiti olmayan aileleri siler.
Sonra yeni alt ailelerin kesitleri: trace_families.py --eksik --uyarlanir.
Her aile bitince dosyaya yazılır; kesilen ölçüm aynı komutla kaldığı yerden devam eder.
Çok üyeli ailelerin hepsi ölçülür. Tek çelikli ailede fark sadece iz elementlerden gelir; arayüz isterse API ölçer.
"""
import argparse
import os
import sys
import time
from datetime import datetime
from multiprocessing import get_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faz_atlasi.calc import sapma  # noqa: E402
from faz_atlasi.calc.engine import get_engine  # noqa: E402
from faz_atlasi.calc.point import SONUC_SURUMU  # noqa: E402
from faz_atlasi.db import AlloyFamily, DataSource, Steel, ensure_schema, make_engine, make_session  # noqa: E402
from faz_atlasi.library import alt_aile  # noqa: E402

_ps = None


def _olc(nom, alasim):
    global _ps
    if _ps is None:
        from faz_atlasi.calc.point import PointService
        _ps = PointService()
    return sapma.olc(_ps, nom, alasim)


def _is(args):
    aile_id, alasim, uyeler, adaylar, kullanilan = args
    t0 = time.time()
    try:
        sonuc = alt_aile.ayir(aile_id, alasim, uyeler, _olc, adaylar, kullanilan)
    except Exception as e:   # tek ailenin hatası bütün ölçümü durdurmasın
        return aile_id, None, f'{type(e).__name__}: {e}', time.time() - t0
    return aile_id, sonuc, None, time.time() - t0


def isler(s, kayit, sadece, yeniden=False):
    oncelik = {d.id: d.priority for d in s.query(DataSource)}
    aileler = {f.id: f for f in s.query(AlloyFamily)}
    uyeler = {}
    for c in s.query(Steel):
        uyeler.setdefault(c.alloy_family_id, []).append(c)
    adaylar = [(f.id, f.base_elements) for f in aileler.values()]
    secilen = []
    for fid, cs in uyeler.items():
        f = aileler.get(fid)
        if f is None or len(cs) < 2 or (sadece and fid not in sadece):
            continue
        if f.parent_id:
            continue    # alt aile: üyeleri zaten ölçülerek buraya geldi
        onceki = kayit['families'].get(fid)
        if not (sadece or yeniden) and onceki and onceki.get('done') and onceki['base'] == f.base_elements:
            continue
        cs.sort(key=lambda c: (oncelik[c.primary_source_id], c.id))
        secilen.append((fid, f, cs))
    # yeniden ölçülen ailelerin eski alt aile kimlikleri serbest kalır
    yeniler = {fid for fid, _, _ in secilen}
    kullanilan = sorted(set(aileler) | {a for a, v in kayit['subfamilies'].items() if v['parent'] not in yeniler})
    out = [(fid, f.base_elements, [(alt_aile.celik_anahtari(c), c.nominal()) for c in cs], adaylar, kullanilan)
           for fid, f, cs in secilen]
    return out, {f.id: f.base_elements for f in aileler.values()}


def kaydet(kayit, aile_id, aile_base, sonuc, tabanlar):
    """Bir ailenin sonucunu kayda işler (aynı ailenin önceki sonucu silinir)."""
    atama, olcumler, yeni = sonuc
    for fid in [f for f, v in kayit['subfamilies'].items() if v['parent'] == aile_id]:
        del kayit['subfamilies'][fid]
    for k in [k for k, v in kayit['steels'].items() if v['parent'] == aile_id]:
        del kayit['steels'][k]
    # paralel işlemler aynı kimliği üretmiş olabilir
    ad = {}
    for fid, (kurucu, base, ust) in yeni.items():
        y, n, kok = fid, 2, fid.split('~')[0]
        while y in kayit['subfamilies'] or y in tabanlar:
            y, n = f'{kok}~{n}', n + 1
        ad[fid] = y
        kayit['subfamilies'][y] = {'parent': ust, 'base': base, 'founder': kurucu}
    taban = {**tabanlar, **{ad[f]: b for f, (_, b, _) in yeni.items()}}
    for k, fid in atama.items():
        if olcumler[k] is None:
            continue    # ölçülemedi (karbonu yok): ailesinde kalır
        fid = ad.get(fid, fid)
        kayit['steels'][k] = {'family': fid, 'parent': aile_id, 'family_base': taban[fid], 'fit': olcumler[k]}
    kayit['families'][aile_id] = {'base': aile_base, 'members': len(atama), 'done': True}
    kayit['meta'] = {'threshold_C': sapma.ESIK, 'tdb_sha': get_engine().tdb_ozet, 'result_version': SONUC_SURUMU,
                     'updated': datetime.now().isoformat(timespec='seconds')}
    return sum(1 for f in atama.values() if f != aile_id), len(yeni)


def olc(a):
    engine = make_engine()
    ensure_schema(engine)    # parent_id sütunu; kısa bir şema değişikliği, çalışan kesit hesabını etkilemez
    s = make_session(engine)
    kayit = alt_aile.kayit_oku()
    liste, tabanlar = isler(s, kayit, set(a.aile), a.yeniden)
    s.close()
    n_celik = sum(len(x[2]) for x in liste)
    print(f'{len(liste)} aile, {n_celik} çelik ölçülecek ({a.islemci} işlem, eşik {sapma.ESIK:g} °C)', flush=True)
    toplam_ayrilan = toplam_yeni = 0
    with get_context('spawn').Pool(a.islemci) as pool:
        for i, (aile_id, sonuc, hata, sure) in enumerate(pool.imap_unordered(_is, liste), 1):
            if hata:
                print(f'[{i}/{len(liste)}] {aile_id}: HATA {hata}', flush=True)
                continue
            ayrilan, yeni = kaydet(kayit, aile_id, tabanlar[aile_id], sonuc, tabanlar)
            alt_aile.kayit_yaz(kayit)
            toplam_ayrilan += ayrilan
            toplam_yeni += yeni
            # ailesine göre fark (ayrılanlarda ayrılmadan önceki fark)
            olcumler = [o.get('parent_fit', o) for o in sonuc[1].values() if o]
            en_buyuk = max((o['max_abs_delta'] for o in olcumler), default=0)
            uyumsuz = sum(1 for o in olcumler if o['mismatch'])
            print(f'[{i}/{len(liste)}] {aile_id}: {len(sonuc[0])} çelik, {ayrilan} ayrıldı ({yeni} yeni alt aile), '
                  f'en büyük fark {en_buyuk:g} °C' + (f', {uyumsuz} yapı farkı' if uyumsuz else '') + f', {sure:.0f} s',
                  flush=True)
    print(f'Bitti: {toplam_ayrilan} çelik ayrıldı, {toplam_yeni} yeni alt aile. Sonra: --uygula', flush=True)


def trace_calisiyor():
    import psutil
    for p in psutil.process_iter(['cmdline']):
        try:
            if any('trace_families' in str(x) for x in (p.info['cmdline'] or [])):
                return True
        except psutil.Error:
            pass
    return False


def uygula(a):
    if trace_calisiyor() and not a.zorla:
        sys.exit('trace_families.py çalışıyor: aileler silinirken çakışmasın diye bitmesini bekleyin (ya da --zorla).')
    engine = make_engine()
    ensure_schema(engine)
    s = make_session(engine)
    tasinan, eklenen, atlanan = alt_aile.uygula(s, alt_aile.kayit_oku())
    silinen = alt_aile.bos_aileleri_sil(s)
    s.commit()
    print(f'{eklenen} alt aile eklendi, {tasinan} çelik taşındı, {silinen} boş aile silindi'
          + (f', {atlanan} kayıt atlandı' if atlanan else ''))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--aile', action='append', default=[], help='sadece bu aile(ler) (yeniden ölçer)')
    p.add_argument('--yeniden', action='store_true', help='daha önce ölçülmüş aileleri de yeniden ölç')
    p.add_argument('--islemci', type=int, default=3)
    p.add_argument('--uygula', action='store_true')
    p.add_argument('--zorla', action='store_true')
    a = p.parse_args()
    uygula(a) if a.uygula else olc(a)


if __name__ == '__main__':
    main()
