"""
Alaşımlı çelikler için dikey kesit (izoplet) hesabı — MatCalc açık çelik veritabanı + pycalphad.
Alaşım elementleri sabit, karbon 0–1.8 % ağ., sıcaklık 550–1100 °C.

  .venv/Scripts/python hesap/kesit_uret.py              # kütüphanedeki tüm çelikler (hesaplanmış olanlar atlanır)
  .venv/Scripts/python hesap/kesit_uret.py 42CrMo4      # tek çelik (ad ya da kesit anahtarı)
  KESIT_ISLEMCI=5 ...                                   # paralel işlem sayısı (bellek yetmezse azalt)

Çelikler hesap/celik_kutuphanesi.py'den gelir. Kesit sadece alaşım elementlerine bağlıdır (karbon eksendir),
bu yüzden aynı alaşımlı çelikler (ör. C35E, C45E) tek kesiti paylaşır.
Çıktı: web/veri/kesit/<anahtar>.js  (her biri KESIT_YUKLE('<anahtar>', {...}) çağırır, seçilince yüklenir)
       web/veri/kesit/liste.js      (window.KESIT_LISTE = hesaplanmış anahtarlar)

Not: pycalphad ızgarası çarpımsal olduğu için alaşım elementlerinin MOL kesri sabit tutulur
(çeliğin nominal karbonunda ağırlıkça değerlerle birebir aynı; karbon değiştikçe ağırlık %'si
çok az kayar — %1.6 C'de bağıl ~%5).

Faz kodları: A=ferrit (BCC_A2), G=östenit (FCC_A1), C=sementit, K7=M7C3, K23=M23C6, K6=M6C,
             MC=MC karbür (FCC_A1 ikinci kompozisyon kümesi, VC vb.), M2C=HCP_A3 (Mo2C vb.), L=sıvı
"""
import json, os, sys, time, warnings
from multiprocessing import Pool
import numpy as np

warnings.filterwarnings('ignore')
BURASI = os.path.dirname(os.path.abspath(__file__))
TDB = os.path.join(BURASI, 'tdb', 'mc_fe_pycalphad.tdb')
FAZLAR = ['LIQUID', 'FCC_A1', 'BCC_A2', 'CEMENTITE', 'M7C3', 'M23C6', 'M6C', 'HCP_A3']
KUTLE = {'FE': 55.847, 'C': 12.011, 'MN': 54.938, 'SI': 28.0855, 'CR': 51.996,
         'NI': 58.69, 'MO': 95.94, 'V': 50.9415, 'W': 183.85, 'CU': 63.546}

sys.path.insert(0, BURASI)
import celik_kutuphanesi as kutuphane

CIKTI = os.path.join(BURASI, '..', 'web', 'veri', 'kesit')

T_LIST = list(np.arange(550, 1100 + 0.1, 5.0))
C_GRID = list(np.round(np.concatenate([[0.002, 0.006, 0.01, 0.015, 0.02], np.arange(0.03, 1.8001, 0.03)]), 4))
ARA = 7  # geçiş aralığına konan ara nokta sayısı (sınır hassasiyeti ~0.03/8)

_db = None


def db():
    global _db
    if _db is None:
        from pycalphad import Database
        _db = Database(TDB)
    return _db


def alas_mol(bilesim):
    """Nominal bileşimde alaşım elementlerinin mol kesirleri ve C ağırlık -> mol dönüşümü"""
    w = dict(bilesim); w['FE'] = 100 - sum(w.values())
    n = {e: w[e] / KUTLE[e] for e in w}
    top = sum(n.values())
    return {e: n[e] / top for e in bilesim if e != 'C'}


def wC_to_xC(wC, xa):
    """Alaşım mol kesirleri sabitken, karbon ağırlık %'si -> mol kesri"""
    # x_C bilinmiyor; Fe mol kesri = 1 - x_C - Σxa. Ağırlık: wC = 100 x_C M_C / Σ x M
    sa = sum(xa.values()); ma = sum(x * KUTLE[e] for e, x in xa.items())
    # wC/100 * (x_C M_C + (1 - x_C - sa) M_Fe + ma) = x_C M_C
    f = wC / 100
    pay = f * ((1 - sa) * KUTLE['FE'] + ma)
    payda = KUTLE['C'] - f * (KUTLE['C'] - KUTLE['FE'])
    return pay / payda


def xC_to_wC(xC, xa):
    sa = sum(xa.values()); ma = sum(x * KUTLE[e] for e, x in xa.items())
    top = xC * KUTLE['C'] + (1 - xC - sa) * KUTLE['FE'] + ma
    return 100 * xC * KUTLE['C'] / top


def kod(faz, xC):
    if faz == 'FCC_A1':
        return 'MC' if xC > 0.25 else 'G'
    if faz == 'BCC_A2':
        return 'A'
    return {'CEMENTITE': 'C', 'M7C3': 'K7', 'M23C6': 'K23', 'M6C': 'K6',
            'HCP_A3': 'M2C', 'LIQUID': 'L'}.get(faz, faz)


SIRA = ['L', 'G', 'A', 'C', 'K7', 'K23', 'K6', 'MC', 'M2C']


def hesap(elems, xa, ws, T):
    from pycalphad import equilibrium, variables as v
    xs = [wC_to_xC(w, xa) for w in ws]
    eq = equilibrium(db(), ['FE', 'VA'] + elems, FAZLAR,
                     {**{v.X(e): x for e, x in xa.items()}, v.X('C'): xs, v.T: T + 273.15, v.P: 1e5})
    # diğer koşul boyutları 1 uzunlukta; (nokta, vertex) şekline düzleştir
    nv = eq.Phase.shape[-1]
    ph = eq.Phase.values.reshape(-1, nv)
    npv = eq.NP.values.reshape(-1, nv)
    bilesenler = [str(c) for c in eq.X.coords['component'].values]
    X = {c: eq.X.sel(component=c).values.reshape(-1, nv) for c in bilesenler}
    assert ph.shape[0] == len(ws)
    out = []
    for i in range(len(ws)):
        kutle, karbon = {}, {}
        for j in range(nv):
            p, n = ph[i][j], npv[i][j]
            if not p or not np.isfinite(n) or n < 1e-5:
                continue
            xc = float(X['C'][i][j])
            k = kod(str(p), xc)
            Mfaz = sum(float(X[c][i][j]) * KUTLE[c] for c in bilesenler)   # g/mol atom
            m = float(n) * Mfaz
            wc = 100 * xc * KUTLE['C'] / Mfaz
            # aynı kodlu iki küme gelirse kütle ağırlıklı birleştir
            karbon[k] = (karbon.get(k, 0) * kutle.get(k, 0) + wc * m) / (kutle.get(k, 0) + m)
            kutle[k] = kutle.get(k, 0) + m
        if not kutle:
            out.append(None)
            continue
        top = sum(kutle.values())
        out.append({k: (kutle[k] / top, karbon[k]) for k in kutle})
    return out


def anahtar(f):
    return None if f is None else tuple(sorted(f, key=SIRA.index))


def satir(args):
    elems, xa, T = args
    pts = list(zip(C_GRID, hesap(elems, xa, C_GRID, T)))
    # geçişlerin arasına ara noktalar koy (tek çağrıda)
    ara = []
    for (wa, fa), (wb, fb) in zip(pts, pts[1:]):
        if anahtar(fa) != anahtar(fb):
            ara.extend(np.linspace(wa, wb, ARA + 2)[1:-1])
    if ara:
        pts = sorted(pts + list(zip(ara, hesap(elems, xa, ara, T))), key=lambda p: p[0])
    pts = [p for p in pts if p[1] is not None]
    # bölgeler: aynı faz kümesine sahip ardışık noktalar; sınır iki noktanın ortası
    bolgeler = []
    for i, (w, f) in enumerate(pts):
        k = anahtar(f)
        if bolgeler and bolgeler[-1]['p'] == list(k):
            continue
        sinir = 0.0 if i == 0 else 0.5 * (pts[i - 1][0] + w)
        if bolgeler:
            bolgeler[-1]['x'][1] = round(sinir, 4)
        bolgeler.append({'p': list(k), 'x': [round(sinir, 4), None]})
    bolgeler[-1]['x'][1] = C_GRID[-1]
    # ızgara noktalarındaki faz oranları (ağırlıkça) ve fazların kendi karbonu (% ağ.)
    oran, karbon = {}, {}
    izgara = dict(pts)
    for j, w in enumerate(C_GRID):
        f = izgara.get(w)
        if f:
            for k, (m, wc) in f.items():
                oran.setdefault(k, [0] * len(C_GRID))[j] = round(m, 4)
                karbon.setdefault(k, [None] * len(C_GRID))[j] = round(wc, 4)
    return {'T': T, 'r': bolgeler, 'o': oran, 'c': karbon}


def kesit(anahtar, bilesim, pool):
    t0 = time.time()
    xa = alas_mol(bilesim)
    elems = ['C'] + list(xa)
    rows = pool.map(satir, [(elems, xa, T) for T in T_LIST], chunksize=2)
    print(f'{anahtar}: {len(rows)} satır, {time.time()-t0:.0f} s', flush=True)
    return {
        'anahtar': anahtar,
        'bilesim': {e.capitalize(): w for e, w in bilesim.items()},
        'x_alas': xa,
        'C': C_GRID, 'T': T_LIST,
        'rows': rows,
        'meta': {'veritabani': 'MatCalc mc_fe v2.062 (ODbL), pycalphad 0.11.2', 'fazlar_tdb': FAZLAR},
    }


def gruplar():
    """Kesit anahtarı -> (referans bileşim, o alaşımı paylaşan çelikler)"""
    g = {}
    for c in kutuphane.liste():
        g.setdefault(c['anahtar'], []).append(c)
    out = {}
    for k, cs in g.items():
        nom = cs[0]['nominal']
        # alaşımın mol kesri, bu kesiti paylaşan çeliklerin ortalama karbonunda sabitlenir
        bil = {'C': round(sum(c['nominal']['C'] for c in cs) / len(cs), 3)}
        bil.update({e.upper(): v for e, v in nom.items() if e != 'C' and v > 0})
        out[k] = (bil, [c['ad'] for c in cs])
    return out


def liste_yaz():
    keys = sorted(f[:-3] for f in os.listdir(CIKTI) if f.endswith('.js') and f != 'liste.js')
    with open(os.path.join(CIKTI, 'liste.js'), 'w', encoding='utf-8') as f:
        f.write('window.KESIT_LISTE=' + json.dumps(keys) + ';\n')
    return keys


def main():
    os.makedirs(CIKTI, exist_ok=True)
    tum = gruplar()
    istek = sys.argv[1:]
    secim = [k for k, (b, ads) in tum.items() if not istek or k in istek or set(ads) & set(istek)]
    yapilacak = [k for k in secim if istek or not os.path.exists(os.path.join(CIKTI, k + '.js'))]
    print(f'{len(tum)} farklı alaşım, {len(yapilacak)} kesit hesaplanacak', flush=True)
    # çok bileşenli çeliklerde her işlem büyük ızgara tutuyor; bellek yetmezse KESIT_ISLEMCI ile azalt
    nproc = int(os.environ.get('KESIT_ISLEMCI', max(1, (os.cpu_count() or 2) - 1)))
    with Pool(nproc) as pool:
        for i, k in enumerate(yapilacak, 1):
            bil, ads = tum[k]
            print(f'[{i}/{len(yapilacak)}] {", ".join(ads)}', flush=True)
            veri = kesit(k, bil, pool)
            veri['celikler'] = ads
            gecici = os.path.join(CIKTI, k + '.js.tmp')
            with open(gecici, 'w', encoding='utf-8') as f:
                f.write(f'KESIT_YUKLE({json.dumps(k)},')
                json.dump(veri, f, ensure_ascii=False, separators=(',', ':'))
                f.write(');\n')
            os.replace(gecici, os.path.join(CIKTI, k + '.js'))   # yarım dosya kalmasın
            liste_yaz()
    print('Hazır kesitler:', len(liste_yaz()))


if __name__ == '__main__':
    main()
