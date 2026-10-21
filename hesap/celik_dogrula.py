"""
MatCalc çelik veritabanının (pycalphad için temizlenmiş) doğrulaması.

  .venv/Scripts/python hesap/celik_dogrula.py

1) İkili Fe-C: ötektoid, saf Fe α→γ (cfe_broshe ile karşılaştırma)
2) Bilinen çelikler: Ae1 / Ae3 / Aecm ve kararlı karbürler
"""
import os, sys, time
import numpy as np
from pycalphad import Database, equilibrium, variables as v

TDB = os.path.join(os.path.dirname(__file__), 'tdb', 'mc_fe_pycalphad.tdb')
KUTLE = {'FE': 55.847, 'C': 12.011, 'MN': 54.938, 'SI': 28.0855, 'CR': 51.996,
         'NI': 58.69, 'MO': 95.94, 'V': 50.9415, 'W': 183.85, 'CU': 63.546}
FAZLAR = ['LIQUID', 'FCC_A1', 'BCC_A2', 'CEMENTITE', 'M7C3', 'M23C6', 'M6C', 'HCP_A3']

db = Database(TDB)


def mol_kesri(wt):
    """wt: {'C':0.42, 'CR':1.05, ...} (% ağ., Fe bakiye) -> {v.X(el): x}"""
    w = dict(wt); w['FE'] = 100 - sum(wt.values())
    n = {e: w[e] / KUTLE[e] for e in w}
    top = sum(n.values())
    return {v.X(e): n[e] / top for e in wt}


def fazlar(wt, T_C):
    el = ['FE', 'VA'] + list(wt)
    ph = [p for p in FAZLAR if p in db.phases]
    eq = equilibrium(db, el, ph, {**mol_kesri(wt), v.T: T_C + 273.15, v.P: 1e5})
    names = eq.Phase.values.squeeze()
    nps = eq.NP.values.squeeze()
    out = {}
    for p, n in zip(np.atleast_1d(names), np.atleast_1d(nps)):
        if p and np.isfinite(n) and n > 1e-6:
            out[str(p)] = out.get(str(p), 0) + float(n)
    return out


def tarama(wt, T0, T1, adim):
    sonuc = []
    for T in np.arange(T0, T1 + 1e-9, adim):
        sonuc.append((float(T), fazlar(wt, T)))
    return sonuc


def bisect(wt, lo, hi, kosul, tol=0.5):
    """kosul(fazlar) lo'da False, hi'da True olacak şekilde sınırı bul"""
    while hi - lo > tol:
        m = 0.5 * (lo + hi)
        if kosul(fazlar(wt, m)):
            hi = m
        else:
            lo = m
    return 0.5 * (lo + hi)


def kritikler(ad, wt):
    t = time.time()
    karbur = lambda f: {k for k in f if k in ('CEMENTITE', 'M7C3', 'M23C6', 'M6C', 'HCP_A3')}
    tar = tarama(wt, 600, 1050, 10)
    Ae1 = Ae3 = Aecm = None
    for (Ta, fa), (Tb, fb) in zip(tar, tar[1:]):
        if Ae1 is None and 'FCC_A1' not in fa and 'FCC_A1' in fb:
            Ae1 = bisect(wt, Ta, Tb, lambda f: 'FCC_A1' in f)
        if Ae3 is None and 'BCC_A2' in fa and 'BCC_A2' not in fb:
            Ae3 = bisect(wt, Ta, Tb, lambda f: 'BCC_A2' not in f)
        if Aecm is None and karbur(fa) and not karbur(fb):
            Aecm = bisect(wt, Ta, Tb, lambda f: not karbur(f))
    print(f'\n== {ad}  {wt}  ({time.time()-t:.0f} s)')
    print(f'   Ae1 = {Ae1 and round(Ae1)} °C   Ae3 = {Ae3 and round(Ae3)} °C   Aecm(karbür çözünme) = {Aecm and round(Aecm)} °C')
    for T, f in tar:
        if T in (600, 700, 750, 800, 850, 900, 950):
            print(f'   {T:5.0f} °C: ' + ', '.join(f'{k} {100*n:.1f}%' for k, n in sorted(f.items(), key=lambda x: -x[1])))
    return Ae1, Ae3, Aecm


if __name__ == '__main__':
    # 1) ikili Fe-C
    t = time.time()
    e = {'C': 0.4}
    T_eut = bisect(e, 700, 760, lambda f: 'FCC_A1' in f, tol=0.1)
    T_fe = bisect({'C': 1e-4}, 880, 940, lambda f: 'BCC_A2' not in f, tol=0.1)
    print(f'İkili Fe-C: ötektoid {T_eut:.1f} °C (cfe_broshe 726.5), saf Fe α→γ {T_fe:.1f} °C (911.6)  [{time.time()-t:.0f} s]')

    CELIKLER = {
        'C45':     {'C': 0.45, 'MN': 0.65, 'SI': 0.25},
        '42CrMo4': {'C': 0.42, 'MN': 0.75, 'SI': 0.25, 'CR': 1.05, 'MO': 0.22},
        '16MnCr5': {'C': 0.16, 'MN': 1.15, 'SI': 0.25, 'CR': 0.95},
        '100Cr6':  {'C': 1.00, 'MN': 0.35, 'SI': 0.25, 'CR': 1.50},
    }
    secim = sys.argv[1:] or list(CELIKLER)
    for ad in secim:
        kritikler(ad, CELIKLER[ad])
