"""
Çelik kütüphanesini ve aile kesitlerini sunucusuz web sitesi için statik dosyalara aktarır (GitHub Pages, file://).

  .venv/Scripts/python backend/export_static.py               # web/veri/kutuphane/celikler2.js + web/veri/aile/*.js
  .venv/Scripts/python backend/export_static.py --hesap 6     # önce eksik ısıl işlem rejimlerini ve uyumları hesapla

Sunucu yoksa web/api.js bu dosyalardan "yerel API" kurar: arama, çelik künyesi, aile kesiti, çelik–aile uyumu ve
ısıl işlem rejimi sunucudaki gibi çalışır. Anlık hesap gerektirenler (tıklanan noktanın faz oranları, elle girilen
bileşimin rejimi) sunucusuz yapılamaz; arayüz bunu söyler.

Dosyalar script olarak yüklenir (fetch değil): sayfa çift tıklanıp file:// ile açıldığında da çalışsın diye.
--hesap: ısıl işlem rejimleri (calc/isil_islem.py) backend/data/rejimler.json'da saklanır (TDB ve sonuç sürümüyle;
bileşim değişirse yeniden hesaplanır); ölçülmemiş çelik–aile uyumları steel_family_fit tablosuna yazılır.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from multiprocessing import get_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faz_atlasi.calc import isil_islem, sapma  # noqa: E402
from faz_atlasi.calc.engine import get_engine  # noqa: E402
from faz_atlasi.calc.point import SONUC_SURUMU  # noqa: E402
from faz_atlasi.db import AlloyFamily, Steel, SteelFamilyFit, ensure_schema, make_engine, make_session  # noqa: E402
from faz_atlasi.library import dogrulama  # noqa: E402
from faz_atlasi.library.alt_aile import celik_anahtari  # noqa: E402
from faz_atlasi.library.classify import eksik_elementler  # noqa: E402

KOK = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WEB = os.path.join(KOK, 'web', 'veri')
REJIMLER = os.path.join(KOK, 'backend', 'data', 'rejimler.json')

_ps = None


def _hesap(args):
    """İşçi: bir çeliğin rejimi ve (istenirse) ailesine uyumu."""
    sinif, nom, aile_alasim = args
    global _ps
    if _ps is None:
        from faz_atlasi.calc.point import PointService
        _ps = PointService()
    try:
        rejim = isil_islem.rejim(sinif, nom, _ps)
        uyum = sapma.olc(_ps, nom, aile_alasim) if aile_alasim is not None and nom.get('C') else None
        return rejim, uyum, None
    except Exception as e:      # tek çeliğin hatası bütün hesabı durdurmasın
        return None, None, f'{type(e).__name__}: {e}'


def bilesim_ozeti(sinif, nom):
    return hashlib.sha256(json.dumps([sinif, sorted(nom.items())]).encode()).hexdigest()[:16]


def hesapla(s, islemci):
    """Eksik rejimleri ve uyumları paralel hesaplar."""
    tdb = get_engine().tdb_ozet
    kayit = json.load(open(REJIMLER, encoding='utf-8')) if os.path.exists(REJIMLER) else {}
    isler, kim = [], []
    for c in s.query(Steel):
        k, nom = celik_anahtari(c), c.nominal()
        r = kayit.get(k)
        rejim_eksik = not (r and r['ozet'] == bilesim_ozeti(c.steel_class, nom) and r['tdb'] == tdb
                           and r['surum'] == SONUC_SURUMU)
        fit = s.get(SteelFamilyFit, c.id)
        uyum_eksik = c.family is not None and (fit is None or fit.family_id != c.alloy_family_id)
        if rejim_eksik or uyum_eksik:
            isler.append((c.steel_class, nom, c.family.base_elements if uyum_eksik else None))
            kim.append((c, k, rejim_eksik))
    print(f'{len(isler)} çelik hesaplanacak ({islemci} işlem)', flush=True)
    t0 = time.time()
    with get_context('spawn').Pool(islemci) as pool:
        for i, ((c, k, rejim_eksik), (rejim, uyum, hata)) in enumerate(zip(kim, pool.imap(_hesap, isler)), 1):
            if hata:
                print(f'  ! {c.standard_name}: {hata}', flush=True)
                continue
            if rejim_eksik:
                kayit[k] = {'ozet': bilesim_ozeti(c.steel_class, c.nominal()), 'tdb': tdb, 'surum': SONUC_SURUMU,
                            'rejim': rejim}
            if uyum is not None:
                s.merge(SteelFamilyFit(steel_id=c.id, family_id=c.alloy_family_id, data=uyum,
                                       max_abs_delta=uyum['max_abs_delta'], within=uyum['within'],
                                       checked_at=datetime.utcnow()))
            if i % 20 == 0 or i == len(isler):
                s.commit()
                with open(REJIMLER + '.tmp', 'w', encoding='utf-8') as f:
                    json.dump(kayit, f, ensure_ascii=False, separators=(',', ':'))
                os.replace(REJIMLER + '.tmp', REJIMLER)
                print(f'  {i}/{len(isler)} · {time.time() - t0:.0f} s', flush=True)
    return kayit


def js_yaz(yol, on, veri, son=';\n'):
    """on + JSON + son: ör. 'AILE_YUKLE("Mn1",' + {...} + ');'"""
    gecici = yol + '.tmp'
    with open(gecici, 'w', encoding='utf-8') as f:
        f.write(on)
        json.dump(veri, f, ensure_ascii=False, separators=(',', ':'))
        f.write(son)
    os.replace(gecici, yol)


def aktar(s, rejimler):
    os.makedirs(os.path.join(WEB, 'kutuphane'), exist_ok=True)
    aile_dizin = os.path.join(WEB, 'aile')
    os.makedirs(aile_dizin, exist_ok=True)
    aileler = {f.id: f for f in s.query(AlloyFamily)}

    # aile kesitleri: arayüzün kullandığı alanlar (sınır çizgileri 'lines' arayüzde kullanılmıyor)
    yazilan = set()
    for fid, f in aileler.items():
        b = f.isopleth_boundaries
        if not b:
            continue
        js_yaz(os.path.join(aile_dizin, fid + '.js'), f'AILE_YUKLE({json.dumps(fid)},',
               {k: b[k] for k in ('composition', 'C_ref', 'T', 'C_max', 'rows', 'ignored_elements', 'phases_considered')
                if k in b}, son=');\n')
        yazilan.add(fid + '.js')
    for ad in os.listdir(aile_dizin):          # artık olmayan ailelerin dosyaları
        if ad.endswith('.js') and ad not in yazilan:
            os.remove(os.path.join(aile_dizin, ad))

    celikler = []
    for c in s.query(Steel).order_by(Steel.id):
        fit = s.get(SteelFamilyFit, c.id)
        r = rejimler.get(celik_anahtari(c))
        celikler.append({
            'id': c.id, 'ad': c.standard_name, 'grup': c.group_name, 'grup_en': c.group_name_en,
            'sinif': c.steel_class, 'std': c.standard_code, 'kul': c.usage_tr, 'kul_en': c.usage_en,
            'adlar': [[d.system, d.code, int(d.approx), d.code_norm] for d in c.designations],
            'bil': [[x.element, x.min_val, x.max_val, x.nominal_val]
                    for x in sorted(c.composition, key=lambda x: (x.element != 'C', x.element))],
            'aile': c.alloy_family_id,
            'ust': c.family.parent_id if c.family else None,
            'kaynak': sorted({x.source_id for x in c.sources}),
            'eksik': eksik_elementler(c.nominal()),
            'uyum': fit.data if fit and fit.family_id == c.alloy_family_id else None,
            'rejim': r['rejim'] if r else None,
        })
    veri = {
        'meta': {'olusturma': datetime.now().isoformat(timespec='seconds'), 'tdb_sha': get_engine().tdb_ozet,
                 'model': 'MatCalc mc_fe v2.062 (ODbL) + pycalphad', 'celik': len(celikler),
                 'dogrulama': dogrulama.ozet()},
        'aileler': {fid: {'kesit': fid + '.js' in yazilan, 'ust': f.parent_id} for fid, f in aileler.items()},
        'celikler': celikler,
    }
    yol = os.path.join(WEB, 'kutuphane', 'celikler2.js')
    js_yaz(yol, '// backend/export_static.py ile üretildi — elle düzenleme yapmayın\nwindow.KUTUPHANE_V2=', veri)
    boyut = sum(os.path.getsize(os.path.join(aile_dizin, a)) for a in yazilan)
    print(f'{len(celikler)} çelik ({os.path.getsize(yol) / 1e6:.2f} MB, rejimi olan {sum(1 for c in celikler if c["rejim"])}, '
          f'uyumu olan {sum(1 for c in celikler if c["uyum"])}), {len(yazilan)}/{len(aileler)} aile kesiti '
          f'({boyut / 1e6:.1f} MB)')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--hesap', type=int, metavar='İŞLEM', help='önce eksik rejim ve uyumları bu kadar işlemle hesapla')
    a = p.parse_args()
    if a.hesap and sys.platform == 'win32':
        import ctypes      # uzun hesap sürerken bilgisayar boşta uykuya geçmesin (trace_families.py ile aynı)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    engine = make_engine()
    ensure_schema(engine)
    s = make_session(engine)
    if a.hesap:
        rejimler = hesapla(s, a.hesap)
    else:
        rejimler = json.load(open(REJIMLER, encoding='utf-8')) if os.path.exists(REJIMLER) else {}
    aktar(s, rejimler)


if __name__ == '__main__':
    main()
