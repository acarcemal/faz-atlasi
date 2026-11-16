"""
pycalphad motoru — süreç başına tek örnek (singleton).

TDB bir kez okunur; her element kümesi için faz modelleri ve derlenmiş enerji fonksiyonları (PhaseRecordFactory)
ilk kullanımda kurulup bellekte tutulur. Aynı alaşım sistemine sonraki istekler derleme maliyeti ödemez.

Hesaba giren elementler TDB'nin kendisinden okunur (Engine.destekli). hesap/tdb_temizle.py'nin ürettiği
mc_fe_pycalphad.tdb şu an sadece C, Cr, Cu, Mn, Mo, Ni, Si, V, W içerir; N, Ti, Nb, Al, Co, B, P, S hesap dışıdır
(etkileri ihmal edilir ve yanıtta `ignored_elements` olarak bildirilir).
Bileşimler ağırlıkça %; pycalphad koşulları mol kesri olarak verilir.
"""
import hashlib
import os
import threading
import warnings
from collections import OrderedDict

import numpy as np

warnings.filterwarnings('ignore')

KOK = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TDB = os.environ.get('FAZ_TDB') or os.path.join(KOK, 'hesap', 'tdb', 'mc_fe_pycalphad.tdb')

KUTLE = {'FE': 55.847, 'C': 12.011, 'MN': 54.938, 'SI': 28.0855, 'CR': 51.996, 'NI': 58.69, 'MO': 95.94,
         'V': 50.9415, 'W': 183.85, 'CU': 63.546, 'CO': 58.9332, 'NB': 92.9064, 'TI': 47.88, 'AL': 26.98154,
         'N': 14.0067, 'B': 10.811}
HESAP_DISI = {'P', 'S', 'AS', 'ZR'}

TEMEL_FAZLAR = ['LIQUID', 'FCC_A1', 'BCC_A2', 'CEMENTITE', 'M7C3', 'M23C6', 'M6C', 'HCP_A3']

# Faz kodları hesap/kesit_uret.py ile aynı (web arayüzü bu kodları tanıyor) + paslanmazlar için yeni kodlar
KOD = {'BCC_A2': 'A', 'CEMENTITE': 'C', 'M7C3': 'K7', 'M23C6': 'K23', 'M6C': 'K6', 'HCP_A3': 'M2C',
       'LIQUID': 'L', 'SIGMA': 'SG', 'CHI_A12': 'CHI', 'LAVES_PHASE': 'LAV'}
SIRA = ['L', 'G', 'A', 'C', 'K7', 'K23', 'K6', 'MC', 'M2C', 'SG', 'CHI', 'LAV']


def fazlar_icin(bilesim):
    """Yüksek Cr/Mo'lu çeliklerde intermetalik fazlar da gerekir (σ, χ, Laves)."""
    f = list(TEMEL_FAZLAR)
    if bilesim.get('CR', 0) >= 10:
        f.append('SIGMA')
        if bilesim.get('MO', 0) >= 1:
            f += ['CHI_A12', 'LAVES_PHASE']
    return f


def faz_kodu(faz, x_ara):
    """FCC_A1'in ikinci kompozisyon kümesi MC/MN karbonitrürüdür (VC, NbC, TiN): ara yer atomu oranı yüksek."""
    if faz == 'FCC_A1':
        return 'MC' if x_ara > 0.25 else 'G'
    return KOD.get(faz, faz)


def sira(kodlar):
    return tuple(sorted(kodlar, key=lambda k: SIRA.index(k) if k in SIRA else 99))


def agirlik_to_mol(w):
    """w: element -> ağ.% (Fe hariç, büyük harf). Fe = kalan."""
    w = dict(w)
    w['FE'] = 100 - sum(w.values())
    n = {e: w[e] / KUTLE[e] for e in w}
    top = sum(n.values())
    return {e: n[e] / top for e in n}


def wC_to_xC(wC, xa):
    """Alaşım mol kesirleri (xa, C ve Fe hariç) sabitken karbon ağ.% -> mol kesri (kesit_uret.py ile aynı)."""
    sa = sum(xa.values())
    ma = sum(x * KUTLE[e] for e, x in xa.items())
    f = wC / 100
    return f * ((1 - sa) * KUTLE['FE'] + ma) / (KUTLE['C'] - f * (KUTLE['C'] - KUTLE['FE']))


class Engine:
    # Başlangıç ızgarasının yoğunluğu (calc_opts pdens). None = pycalphad varsayılanı; tek nokta hesabı bununla yapılır.
    # HIZLI_PDENS (~%40 kısa) sadece sınır izlemede tarama için: düşük sıcaklıkta çok karbürlü bölgelerde yanlış faz
    # kümesi verebiliyor (42CrMo4, 550 °C, %0,25 C: A+C+K23; doğrusu A+C+K7), bu yüzden trace.py her bölgeyi
    # varsayılan yoğunlukla doğrular.
    PDENS = int(os.environ['FAZ_PDENS']) if os.environ.get('FAZ_PDENS') else None
    HIZLI_PDENS = 30

    def __init__(self, tdb=TDB, model_kapasite=None):
        self.tdb_yolu = tdb
        self._db = None
        self._modeller = OrderedDict()   # (elementler, fazlar) -> (models, prf); LRU
        # toplu kesit hesabında işlemler aileden aileye geçer: eski sistemleri bellekte tutmamak için küçük tutulur
        self._kapasite = model_kapasite or int(os.environ.get('FAZ_MODEL_CACHE', 16))
        self.kilit = threading.Lock()     # pycalphad iş parçacığı güvenli değil; çağrılar sıraya girer
        with open(tdb, 'rb') as f:
            self.tdb_ozet = hashlib.sha256(f.read()).hexdigest()[:16]
        self._destekli = None

    @property
    def destekli(self):
        """Matris fazlarında (FCC/BCC) tanımlı elementler — hesap bunlarla yapılabilir."""
        if self._destekli is None:
            el = set()
            for faz in ('FCC_A1', 'BCC_A2'):
                for alt in self.db.phases[faz].constituents:
                    el |= {str(s.name) for s in alt}
            self._destekli = (el - {'VA', 'FE'}) & set(KUTLE)
        return self._destekli

    @property
    def db(self):
        if self._db is None:
            from pycalphad import Database
            self._db = Database(self.tdb_yolu)
        return self._db

    def hazir(self, elems, fazlar):
        anahtar = (tuple(elems), tuple(fazlar))
        if anahtar in self._modeller:
            self._modeller.move_to_end(anahtar)
            return self._modeller[anahtar]
        from pycalphad import variables as v
        from pycalphad.codegen.phase_record_factory import PhaseRecordFactory
        from pycalphad.core.utils import instantiate_models, unpack_species
        comps = ['FE', 'VA'] + list(elems)
        models = instantiate_models(self.db, comps, fazlar)
        prf = PhaseRecordFactory(self.db, sorted(unpack_species(self.db, comps)), [v.N, v.P, v.T], models)
        self._modeller[anahtar] = (models, prf)
        if len(self._modeller) > self._kapasite:
            self._modeller.popitem(last=False)
        return models, prf

    def coz(self, xa, xCs, T_C, fazlar, pdens=None):
        """
        Sabit alaşım mol kesirleri (xa) ve bir dizi karbon mol kesri için denge.
        Dönüş: her nokta için {kod: {'w': kütle kesri, 'X': {element: mol kesri}}} ya da çözüm yoksa None.
        """
        from pycalphad import equilibrium, variables as v
        elems = ['C'] + sorted(xa)
        models, prf = self.hazir(elems, fazlar)
        eq = equilibrium(self.db, ['FE', 'VA'] + elems, fazlar,
                         {**{v.X(e): x for e, x in xa.items()}, v.X('C'): list(xCs), v.T: T_C + 273.15,
                          v.P: 1e5, v.N: 1},
                         model=models, phase_records=prf,
                         calc_opts={'pdens': pdens or self.PDENS} if (pdens or self.PDENS) else None)
        nv = eq.Phase.shape[-1]
        ph = eq.Phase.values.reshape(-1, nv)
        npv = eq.NP.values.reshape(-1, nv)
        bilesenler = [str(c) for c in eq.X.coords['component'].values]
        X = {c: eq.X.sel(component=c).values.reshape(-1, nv) for c in bilesenler}
        out = []
        for i in range(len(xCs)):
            kutle, xs = {}, {}
            for j in range(nv):
                p, n = ph[i][j], npv[i][j]
                if not p or not np.isfinite(n) or n < 1e-5:
                    continue
                xj = {c: float(X[c][i][j]) for c in bilesenler}
                k = faz_kodu(str(p), xj.get('C', 0) + xj.get('N', 0))
                m = float(n) * sum(xj[c] * KUTLE[c] for c in bilesenler)
                # aynı kodlu iki küme gelirse kütle ağırlıklı birleştir
                eski = kutle.get(k, 0)
                xs[k] = {c: (xs.get(k, {}).get(c, 0) * eski + xj[c] * m) / (eski + m) for c in bilesenler}
                kutle[k] = eski + m
            if not kutle:
                out.append(None)
                continue
            top = sum(kutle.values())
            out.append({k: {'w': kutle[k] / top, 'X': xs[k]} for k in kutle})
        return out

    def coz_saglam(self, xa, xCs, T_C, fazlar, pdens=None):
        """Çözücünün nadiren sonuç vermediği noktalar karbon çok az kaydırılarak yeniden denenir."""
        out = self.coz(xa, xCs, T_C, fazlar, pdens)
        for i, r in enumerate(out):
            for d in (1e-5, -1e-5, 1e-4, -1e-4):
                if r is not None:
                    break
                if xCs[i] + d > 0:
                    r = out[i] = self.coz(xa, [xCs[i] + d], T_C, fazlar, pdens)[0]
        return out


def faz_bilesimi_agirlik(X):
    """Faz mol kesirleri -> ağ.%"""
    M = sum(x * KUTLE[e] for e, x in X.items())
    return {e: 100 * x * KUTLE[e] / M for e, x in X.items()}


_motor = None
_motor_kilit = threading.Lock()


def get_engine():
    global _motor
    with _motor_kilit:
        if _motor is None:
            _motor = Engine()
        return _motor
