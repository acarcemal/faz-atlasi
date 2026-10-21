"""
Fe-Fe3C (metastabil) faz diyagramı verisini pycalphad ile hesaplar ve
web/veri/fe_c.json dosyasına yazar.

Veri yapısı:
  rows: her sıcaklık için karbon ekseni boyunca bölgeler listesi
        [{"p": ["A","C"], "x": [sol_sinir_wt, sag_sinir_wt]}, ...]
        İki fazlı bölgede x uçları bağlantı çizgisinin (tie-line) uçlarıdır,
        yani o sıcaklıkta iki fazın kendi karbon oranları.
  invariants: ötektoid / ötektik / peritektik ve saf Fe dönüşümleri

Faz kodları: A = α-ferrit, D = δ-ferrit (ikisi de BCC_A2), G = östenit (FCC_A1),
             L = sıvı, C = sementit (Fe3C)

Çalıştırma:  .venv/Scripts/python hesap/diyagram_uret.py
"""
import json, os, sys, time
from multiprocessing import Pool
import numpy as np

PHASES = ['BCC_A2', 'CEMENTITE_D011', 'FCC_A1', 'LIQUID']   # grafit yok -> metastabil
P = 1e5
M_C, M_FE = 12.011, 55.847
W_CEM = 100 * M_C / (M_C + 3 * M_FE)                       # Fe3C = %6.69 C
T_MIN, T_MAX = 400, 1600

_db = None


def db():
    global _db
    if _db is None:
        import pycalphad
        from pycalphad import Database
        _db = Database(os.path.join(os.path.dirname(pycalphad.__file__),
                                    'tests', 'databases', 'cfe_broshe.tdb'))
    return _db


def w2x(w):
    a = w / M_C; b = (100 - w) / M_FE
    return a / (a + b)


def x2w(x):
    return 100 * x * M_C / (x * M_C + (1 - x) * M_FE)


def code(name, T):
    if name == 'BCC_A2':
        return 'A' if T < 1200 else 'D'
    return {'FCC_A1': 'G', 'LIQUID': 'L', 'CEMENTITE_D011': 'C'}[name]


def eq_points(T_C, ws):
    """Verilen sıcaklık ve ağırlık % listesi için her noktanın faz kümesini döndürür.
    Sonuç: [(w, [(faz, w_faz, oran), ...]), ...]"""
    from pycalphad import equilibrium, variables as v
    xs = [w2x(w) for w in ws]
    eq = equilibrium(db(), ['FE', 'C', 'VA'], PHASES,
                     {v.X('C'): xs, v.T: [T_C + 273.15], v.P: P})
    phs = eq.Phase.values[0, 0, 0]
    xcs = eq.X.sel(component='C').values[0, 0, 0]
    nps = eq.NP.values[0, 0, 0]
    out = []
    for i, w in enumerate(ws):
        sets = {}
        for ph, xc, n in zip(phs[i], xcs[i], nps[i]):
            if not ph or not np.isfinite(n) or n < 1e-9:
                continue
            c = code(str(ph), T_C)
            wc = x2w(float(xc))
            # aynı fazın iki kompozisyon kümesi gelirse (yakınsa) birleştir
            if c in sets and abs(sets[c][0] - wc) < 1e-3:
                sets[c] = (sets[c][0], sets[c][1] + float(n))
            elif c in sets:
                c2 = c + '2'
                sets[c2] = (wc, float(n))
            else:
                sets[c] = (wc, float(n))
        out.append((w, sorted([(k, s[0], s[1]) for k, s in sets.items()], key=lambda t: t[1])))
    return out


def phase_key(pt):
    return tuple(p[0] for p in pt[1])


GRID = np.unique(np.round(np.concatenate([
    np.arange(0.0005, 0.03, 0.0005),
    np.arange(0.03, 0.25, 0.005),
    np.arange(0.25, W_CEM - 0.02, 0.04),
    [W_CEM - 0.01],
]), 5))


def find_transition(T, wa, wb, ka, kb, depth=0):
    """İki komşu tek fazlı nokta arasındaki kaçırılmış iki fazlı bölgeyi ikiye bölerek bul."""
    pts = eq_points(T, list(np.linspace(wa, wb, 9)[1:-1]))
    for p in pts:
        if len(p[1]) == 2:
            return p
    if depth < 3:
        keys = [phase_key(p) for p in pts]
        for i in range(len(pts) - 1):
            if keys[i] != keys[i + 1]:
                return find_transition(T, pts[i][0], pts[i + 1][0], keys[i], keys[i + 1], depth + 1)
    return None


def row(T):
    pts = eq_points(T, list(GRID))
    # tek fazlı komşular arasında atlanmış iki fazlı bölge var mı?
    extra = []
    for a, b in zip(pts, pts[1:]):
        ka, kb = phase_key(a), phase_key(b)
        if len(ka) == 1 and len(kb) == 1 and ka != kb:
            p = find_transition(T, a[0], b[0], ka, kb)
            if p:
                extra.append(p)
    pts = sorted(pts + extra, key=lambda p: p[0])

    # iki fazlı segmentleri topla
    segs = []
    for w, ph in pts:
        if len(ph) != 2:
            continue
        key = (ph[0][0], ph[1][0])
        xl, xr = ph[0][1], ph[1][1]
        if segs and segs[-1]['p'] == list(key):
            segs[-1]['_xl'].append(xl); segs[-1]['_xr'].append(xr)
        else:
            segs.append({'p': list(key), '_xl': [xl], '_xr': [xr]})
    two = []
    for s in segs:
        two.append({'p': s['p'], 'x': [float(np.median(s['_xl'])), float(np.median(s['_xr']))]})

    # tek fazlı boşlukları doldur
    regions = []
    cursor = 0.0
    first_phase = pts[0][1][0][0] if pts[0][1] else None
    prev_phase = first_phase
    for s in two:
        if s['x'][0] > cursor + 1e-7:
            regions.append({'p': [prev_phase if regions else s['p'][0]], 'x': [cursor, s['x'][0]]})
        regions.append(s)
        cursor = s['x'][1]
        prev_phase = s['p'][1]
    if cursor < W_CEM - 1e-4:
        last = pts[-1][1]
        regions.append({'p': [last[0][0]] if len(last) == 1 else [prev_phase], 'x': [cursor, W_CEM]})
    for r in regions:
        r['x'] = [round(r['x'][0], 5), round(r['x'][1], 5)]
    return {'T': round(T, 3), 'r': regions}


def phase_set_at(T, w):
    return phase_key(eq_points(T, [w])[0])


def bisect_T(w, lo, hi, tol=0.01):
    """lo ve hi sıcaklıklarında faz kümesi farklı; geçiş sıcaklığını bul."""
    klo = phase_set_at(lo, w)
    while hi - lo > tol:
        m = 0.5 * (lo + hi)
        if phase_set_at(m, w) == klo:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def invariants():
    inv = {}
    # Ötektoid: %0.4 C'de α+Fe3C -> α+γ
    T = bisect_T(0.4, 700, 760)
    above = dict((p[0], p[1]) for p in eq_points(T + 0.02, [0.4])[0][1])
    below = dict((p[0], p[1]) for p in eq_points(T - 0.02, [0.4])[0][1])
    inv['otektoid'] = {'T': T, 'G': above['G'], 'A': below['A'], 'C': W_CEM}
    # Ötektik: %3 C'de γ+Fe3C -> γ+L
    T = bisect_T(3.0, 1120, 1180)
    above = dict((p[0], p[1]) for p in eq_points(T + 0.02, [3.0])[0][1])
    below = dict((p[0], p[1]) for p in eq_points(T - 0.02, [3.0])[0][1])
    inv['otektik'] = {'T': T, 'L': above['L'], 'G': below['G'], 'C': W_CEM}
    # Peritektik: %0.3 C'de γ+L -> δ+L
    T = bisect_T(0.3, 1485, 1505)
    above = dict((p[0], p[1]) for p in eq_points(T + 0.02, [0.3])[0][1])
    below = dict((p[0], p[1]) for p in eq_points(T - 0.02, [0.3])[0][1])
    inv['peritektik'] = {'T': T, 'D': above['D'], 'L': above['L'], 'G': below['G']}
    # Saf Fe dönüşümleri (çok düşük C)
    w0 = 1e-5
    inv['Fe_alfa_gama'] = {'T': bisect_T(w0, 880, 940)}
    inv['Fe_gama_delta'] = {'T': bisect_T(w0, 1370, 1420)}
    inv['Fe_ergime'] = {'T': bisect_T(w0, 1520, 1560)}
    # α'nın maksimum C çözünürlüğü (ötektoid sıcaklığı) zaten inv['otektoid']['A']
    return inv


def main():
    t0 = time.time()
    inv = invariants()
    print('Değişmez noktalar:', json.dumps(inv, indent=1), f'({time.time()-t0:.0f} s)', flush=True)

    Ts = set(np.round(np.arange(T_MIN, T_MAX + 0.5, 1.0), 3))
    for k, d in inv.items():
        for dt in (-0.05, 0.05):
            if T_MIN < d['T'] + dt < T_MAX:
                Ts.add(round(d['T'] + dt, 3))
    Ts = sorted(Ts)
    nproc = max(1, (os.cpu_count() or 2) - 1)
    print(f'{len(Ts)} sıcaklık satırı, {len(GRID)} bileşim noktası, {nproc} işlemci', flush=True)
    rows = []
    with Pool(nproc) as pool:
        for i, r in enumerate(pool.imap(row, Ts, chunksize=8)):
            rows.append(r)
            if i % 100 == 0:
                print(f'  {i}/{len(Ts)}  T={r["T"]}  ({time.time()-t0:.0f} s)', flush=True)

    out = {
        'meta': {
            'aciklama': 'Metastabil Fe-Fe3C faz diyagramı, pycalphad CALPHAD hesabı',
            'veritabani': 'cfe_broshe.tdb (Fei & Brosh 2014)',
            'fazlar_tdb': PHASES,
            'basinc_Pa': P,
            'birim': 'karbon: ağırlık %, sıcaklık: °C',
            'W_Fe3C': W_CEM,
            'T_min': T_MIN, 'T_max': T_MAX,
            'faz_kodlari': {'A': 'α-ferrit', 'D': 'δ-ferrit', 'G': 'Östenit (γ)',
                            'L': 'Sıvı', 'C': 'Sementit (Fe₃C)'},
            'uretim_saniye': round(time.time() - t0),
        },
        'invariants': inv,
        'rows': rows,
    }
    path = os.path.join(os.path.dirname(__file__), '..', 'web', 'veri', 'fe_c.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    # file:// ile açılınca fetch çalışmadığı için aynı veri bir de JS olarak
    with open(path[:-5] + '.js', 'w', encoding='utf-8') as f:
        f.write('window.FE_C_DATA=')
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    print('Yazıldı:', os.path.abspath(path), f'{os.path.getsize(path)/1024:.0f} KB',
          f'toplam {time.time()-t0:.0f} s')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        for T in (700, 800, 1000, 1200, 1450, 1500):
            print(json.dumps(row(T), ensure_ascii=False))
    else:
        main()
