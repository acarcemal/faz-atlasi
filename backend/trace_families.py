"""
Alaşım ailelerinin dikey kesitlerini sınır izleme ile hesaplayıp veritabanına (alloy_families.isopleth_boundaries) yazar.

  .venv/Scripts/python backend/trace_families.py Mn0.75_Si0.25_Cr1.05_Mo0.225   # tek aile
  .venv/Scripts/python backend/trace_families.py --eksik --uyarlanir             # hesaplanmamış tüm aileler
  .venv/Scripts/python backend/trace_families.py --celik 42CrMo4                  # bir çeliğin ailesi

--parca K/N: ailenin kimliğinden (crc32 mod N) seçilen K. parça; iki bilgisayara bölüşmek için, ör. burada
  --parca 1,2/3, ikinci bilgisayarda --parca 3/3. Parça aileye bağlı olduğu için iki bilgisayar farklı anlarda
  başlasa da (eksik listesi farklı olsa da) paylar çakışmaz. Sonuçlar merge_isopleths.py ile birleşir.
--uyarlanir: işlem sayısını boş belleğe göre her aileden önce yeniden seçer ve hesap sürerken belleği izler.
  * İşlem başına bellek, bir önceki ailelerde ölçülen en yüksek değerden öğrenilir (alaşım element sayısına göre).
  * Kullanılabilir bellek --rezerv'in altına inmeyecek kadar işlem açılır (en çok çekirdek − 1).
  * Hesap sürerken kullanılabilir bellek --kritik'in altına düşerse havuz durdurulur, aile daha az işlemle
    yeniden hesaplanır (bilgisayar donmasın diye). Kararlar günlüğe yazılır.
Her aile bitince veritabanına yazılır; kesilen hesap aynı komutla kaldığı yerden devam eder.
"""
import argparse
import os
import sys
import threading
import time
import zlib
from datetime import datetime
from multiprocessing import get_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faz_atlasi.calc.engine import get_engine  # noqa: E402
from faz_atlasi.calc.trace import isopleth  # noqa: E402
from faz_atlasi.db import AlloyFamily, Steel, make_engine, make_session  # noqa: E402
from faz_atlasi.library.search import search  # noqa: E402

GB = 2 ** 30


def aile_girdisi(s, f, destekli):
    """Ailenin hesap bileşimi: TDB'de olmayan elementler çıkarılır; karbon referansı üyelerin ortalaması."""
    uyeler = s.query(Steel).filter_by(alloy_family_id=f.id).all()
    cs = [c.nominal().get('C', 0.2) for c in uyeler] or [0.2]
    C_ref = round(min(max(sum(cs) / len(cs), 0.05), 1.2), 3)
    bil = {e.upper(): v for e, v in f.base_elements.items() if e.upper() in destekli}
    yok = sorted(e for e in f.base_elements if e.upper() not in destekli)
    return bil, C_ref, yok


class Bellek:
    """Kullanılabilir belleği izler, havuz işlemlerinin bellek kullanımını ölçer, kritik durumda havuzu durdurur."""

    def __init__(self, rezerv, kritik, en_cok):
        import psutil
        self.ps = psutil
        self.rezerv, self.kritik, self.en_cok = rezerv * GB, kritik * GB, en_cok
        self.olcum = {}            # alaşım element sayısı -> işlem başına en yüksek bellek (bayt)
        self.havuz = None
        self.tepe = 0              # bu ailede işlem başına görülen en yüksek bellek
        self.tasma = False
        self._dur = threading.Event()
        threading.Thread(target=self._izle, daemon=True).start()

    def kullanilabilir(self):
        return self.ps.virtual_memory().available

    def _cocuklar(self):
        try:
            return [p.memory_info().rss for p in self.ps.Process().children(recursive=True)]
        except self.ps.Error:
            return []

    def _izle(self):
        while not self._dur.wait(2):
            rss = self._cocuklar()
            if rss:
                self.tepe = max(self.tepe, max(rss))
            if self.kullanilabilir() < self.kritik:
                self.tasma = True

    def islem_basi(self, n_el):
        """Ölçüm varsa en yakın element sayısındaki ölçüm (+%15 pay), yoksa kaba tahmin."""
        if self.olcum:
            yakin = min(self.olcum, key=lambda k: (abs(k - n_el), -k))
            return self.olcum[yakin] * (1.15 + 0.1 * max(0, n_el - yakin))
        return (0.6 + 0.12 * n_el) * GB

    def sec(self, n_el, mevcut_havuz_bellegi=0):
        """Açılabilecek işlem sayısı. Var olan havuzun belleği zaten kullanılıyor sayılır."""
        bos = self.kullanilabilir() + mevcut_havuz_bellegi - self.rezerv
        return max(1, min(self.en_cok, int(bos // self.islem_basi(n_el))))

    def kaydet(self, n_el):
        if self.tepe:
            self.olcum[n_el] = max(self.olcum.get(n_el, 0), self.tepe)

    def havuz_bellegi(self):
        return sum(self._cocuklar())


class BellekTasmasi(Exception):
    pass


class GozetimliHavuz:
    """isopleth()'e verilen havuz: map'i parça parça bekler, bellek kritikse havuzu durdurup BellekTasmasi atar.
    (Pool.terminate() bekleyen map'i hata vermeden asılı bırakabildiği için bekleme burada yapılır.)"""

    def __init__(self, n, bellek):
        self.pool = get_context('spawn').Pool(n)
        self.bellek = bellek

    def map(self, f, isler, chunksize=1):
        r = self.pool.map_async(f, isler, chunksize=chunksize)
        while not r.ready():
            r.wait(2)
            if self.bellek and self.bellek.tasma:
                self.kapat()
                raise BellekTasmasi()
        return r.get()

    def kapat(self):
        self.pool.terminate()
        self.pool.join()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('aileler', nargs='*')
    p.add_argument('--celik', action='append', default=[])
    p.add_argument('--eksik', action='store_true', help='kesiti olmayan tüm aileler')
    p.add_argument('--islemci', type=int, default=int(os.environ.get('FAZ_TRACE_PROCS', 4)))
    p.add_argument('--uyarlanir', action='store_true', help='işlem sayısını boş belleğe göre ayarla')
    p.add_argument('--rezerv', type=float, default=2.5, help='diğer programlara bırakılacak bellek, GB')
    p.add_argument('--kritik', type=float, default=1.0, help='bunun altına inilirse havuzu durdur, GB')
    p.add_argument('--dT', type=float, default=5)
    p.add_argument('--parca', help='K/N ya da K1,K2/N: sıralı listenin bu parçaları (bilgisayarlar arası bölüşme)')
    p.add_argument('--ters', action='store_true',
                   help='listeyi sondan başla (öbür bilgisayar baştan giderken ortada buluşmak için)')
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
    if a.parca:
        ks, n = a.parca.split('/')
        ks, n = {int(k) for k in ks.split(',')}, int(n)
        # sıradaki yere göre bölmek, listesi farklı anlarda alınan iki bilgisayarda payları kaydırıyordu
        hedef = [fid for fid in sorted(hedef) if zlib.crc32(fid.encode()) % n + 1 in ks]
    if a.ters:
        hedef = sorted(hedef, reverse=True)
    destekli = get_engine().destekli
    en_cok = max(1, (os.cpu_count() or 2) - 1)
    bellek = Bellek(a.rezerv, a.kritik, en_cok) if a.uyarlanir else None
    print(f'{len(hedef)} aile, ' + (f'uyarlanır (en çok {en_cok} işlem, {a.rezerv:g} GB rezerv)' if bellek
                                   else f'{a.islemci} işlem'), flush=True)

    # Windows'ta hesap sürerken bilgisayar boşta uykuya geçmesin (ayar değiştirmez; işlem bitince kendiliğinden kalkar)
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    # işlemler aileden aileye korunur (TDB her ailede yeniden okunmaz); sayı değişince havuz yeniden kurulur
    os.environ.setdefault('FAZ_MODEL_CACHE', '2')
    havuz, n_havuz = None, 0
    try:
        for i, fid in enumerate(hedef, 1):
            f = s.get(AlloyFamily, fid, populate_existing=True)
            if not f:
                print(f'  aile yok: {fid}')
                continue
            if a.eksik and f.isopleth_boundaries is not None:
                # hesap sürerken başka bir bilgisayarın sonucu birleştirildi (merge_isopleths.py)
                print(f'[{i}/{len(hedef)}] {fid}: başka yerde hesaplandı, atlandı', flush=True)
                continue
            bil, C_ref, yok = aile_girdisi(s, f, destekli)
            n_el = len(bil)
            while True:
                n = bellek.sec(n_el, bellek.havuz_bellegi() if havuz else 0) if bellek else a.islemci
                if havuz is None or n != n_havuz:
                    if havuz:
                        havuz.kapat()
                    havuz, n_havuz = (GozetimliHavuz(n, bellek) if n > 1 else None), n
                if bellek:
                    bellek.tepe, bellek.tasma = 0, False
                t0 = time.time()
                try:
                    sonuc = isopleth(bil, C_ref, dT=a.dT, islemci=n, havuz=havuz)
                    break
                except BellekTasmasi:
                    # bellek kritik seviyeye indi: havuz durduruldu, ölçüm büyütülüp daha az işlemle yeniden
                    print(f'  ! kullanılabilir bellek {bellek.kullanilabilir() / GB:.1f} GB\'a düştü, {n} işlem durduruldu; '
                          'daha az işlemle yeniden', flush=True)
                    bellek.olcum[n_el] = max(bellek.olcum.get(n_el, 0), bellek.tepe, bellek.islem_basi(n_el)) * 1.3
                    havuz = None
                    if n == 1:
                        time.sleep(30)
            if bellek:
                bellek.kaydet(n_el)
            sonuc['ignored_elements'] = yok
            f.isopleth_boundaries = sonuc
            f.calculated_at = datetime.utcnow()
            s.commit()
            ek = (f' | {n} işlem, işlem başı {bellek.tepe / GB:.2f} GB, kullanılabilir {bellek.kullanilabilir() / GB:.1f} GB'
                  if bellek else '')
            print(f'[{i}/{len(hedef)}] {fid}: {time.time() - t0:.0f} s, {sonuc["meta"]["points"]} nokta'
                  + (f' (hesap dışı: {", ".join(yok)})' if yok else '') + ek, flush=True)
    finally:
        if havuz:
            havuz.kapat()


if __name__ == '__main__':
    main()
