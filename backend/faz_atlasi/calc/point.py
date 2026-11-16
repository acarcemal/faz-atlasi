"""
Tek nokta denge hesabı + önbellek.

Önbellek iki katmanlı: süreç içi LRU (en hızlı) ve isteğe bağlı kalıcı katman (calculation_cache tablosu).
Anahtar: SHA256(bileşim [4 ondalık] + T [0,1 °C] + P + TDB özeti + faz listesi). TDB değişirse eski sonuçlar
kendiliğinden geçersiz olur.
"""
import hashlib
import json
import time
from collections import OrderedDict

from .engine import HESAP_DISI, KUTLE, agirlik_to_mol, faz_bilesimi_agirlik, fazlar_icin, get_engine, sira


class GecersizBilesim(ValueError):
    pass


def bilesim_duzenle(bilesim, destekli):
    """{'C': 0.42, 'Cr': 1.05, 'N': 0.05} -> ({'C': 0.42, 'CR': 1.05}, ['N'])"""
    w, yok = {}, []
    for e, val in bilesim.items():
        E = e.strip().upper()
        if E == 'FE':
            continue
        if E not in KUTLE and E not in HESAP_DISI:
            raise GecersizBilesim(f'Bilinmeyen element: {e}')
        if val < 0:
            raise GecersizBilesim(f'{e} negatif olamaz')
        if E != 'C' and E not in destekli:
            if val > 0:
                yok.append(E.capitalize())
            continue
        if val > 0:
            w[E] = round(float(val), 4)
    if 'C' not in w:
        raise GecersizBilesim('Karbon (C) gerekli')
    if sum(w.values()) >= 60:
        raise GecersizBilesim('Alaşım toplamı %60 ağ. altında olmalı (Fe esaslı model)')
    return w, yok


def onbellek_anahtari(w, T, fazlar, tdb_ozet):
    ham = json.dumps({'w': sorted(w.items()), 'T': round(T, 1), 'P': 1e5, 'tdb': tdb_ozet, 'f': fazlar},
                     separators=(',', ':'))
    return hashlib.sha256(ham.encode()).hexdigest()


class PointService:
    def __init__(self, engine=None, lru_kapasite=5000, kalici=None):
        """kalici: (oku(anahtar) -> dict|None, yaz(anahtar, dict)) çifti; None ise sadece bellek."""
        self.engine = engine or get_engine()
        self.lru = OrderedDict()
        self.kapasite = lru_kapasite
        self.kalici = kalici

    def hesapla(self, bilesim, T):
        w, yok = bilesim_duzenle(bilesim, self.engine.destekli)
        fazlar = fazlar_icin(w)
        anahtar = onbellek_anahtari(w, T, fazlar, self.engine.tdb_ozet)
        t0 = time.perf_counter()
        sonuc, kaynak = self.lru.get(anahtar), 'memory'
        if sonuc is None and self.kalici:
            sonuc, kaynak = self.kalici[0](anahtar), 'database'
        if sonuc is None:
            sonuc, kaynak = self._coz(w, T, fazlar), None
            if self.kalici:
                self.kalici[1](anahtar, sonuc)
        self.lru[anahtar] = sonuc
        self.lru.move_to_end(anahtar)
        if len(self.lru) > self.kapasite:
            self.lru.popitem(last=False)
        return {**sonuc, 'ignored_elements': yok, 'cached': kaynak is not None, 'cache_layer': kaynak,
                'elapsed_ms': round((time.perf_counter() - t0) * 1000, 1)}

    def _coz(self, w, T, fazlar):
        x = agirlik_to_mol(w)
        xa = {e: v for e, v in x.items() if e not in ('C', 'FE')}
        with self.engine.kilit:
            r = self.engine.coz_saglam(xa, [x['C']], T, fazlar)[0]
        if r is None:
            raise RuntimeError('Denge çözümü bulunamadı')
        kodlar = sira(r)
        bil = {k: faz_bilesimi_agirlik(r[k]['X']) for k in kodlar}
        return {
            'T': T,
            'composition': {e.capitalize(): v for e, v in w.items()},
            'phases': {k: round(r[k]['w'], 5) for k in kodlar},
            'carbon_in_phases': {k: round(bil[k].get('C', 0), 4) for k in kodlar},
            'phase_compositions': {k: {e.capitalize(): round(v, 4) for e, v in bil[k].items() if v >= 1e-4}
                                   for k in kodlar},
            'phases_considered': fazlar,
            'model': 'MatCalc mc_fe v2.062 (ODbL) + pycalphad',
        }
