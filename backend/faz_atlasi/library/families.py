"""
Alaşım kümeleme (alloy clustering).

Karbon kesitin x ekseni olduğu için karbon dışındaki bileşimi birbirine yeterince yakın çelikler aynı dikey
kesiti paylaşır (25CrMo4 / 42CrMo4 / 50CrMo4). Kural:
  * Sadece TDB'de olan ve faz dengesini etkileyen elementler dikkate alınır (P, S, As, Zr dışarıda).
  * İki bileşim, her elementte |fark| <= max(mutlak tolerans, %REL * değer) ise aynı ailededir (yoksa 0 sayılır).
  * Açgözlü (greedy) ve deterministik: çelikler kaynak önceliğine göre sırayla gezilir; ilk uyan aileye girer,
    uymazsa kendi bileşimiyle yeni aile kurar (kurucu). Ailenin bileşimi kurucunun nominal bileşimidir.
  * Aile kimliği kurucunun bileşiminden üretilir ve mevcut kesitlerin anahtarıyla aynı biçimdedir
    (hesap/celik_kutuphanesi.py: alas_anahtari); böylece web/veri/kesitler.js'teki hesaplar yeniden kullanılabilir.

Toleranslar yaklaşık A1/A3 kayması ~5-10 °C mertebesinde kalacak şekilde seçildi; ayarlanabilir.
"""

# Mevcut kesit anahtarlarındaki sıra korunur, yeni elementler sona eklenir
SIRA = ['Mn', 'Si', 'Cr', 'Ni', 'Mo', 'V', 'W', 'Cu', 'Co', 'Nb', 'Ti', 'Al', 'N', 'B']

# Si: açık veri setleri sakinleştirilmiş karbon çeliklerinde Si'yi çoğu zaman hiç vermiyor (0), standart tipik
# değeri 0,25; 0,30 tolerans bu ikisini aynı kesitte toplar (Si 0,25 farkı A3'ü yalnızca birkaç °C kaydırır).
MUTLAK_TOL = {'Mn': 0.20, 'Si': 0.30, 'Cr': 0.20, 'Ni': 0.20, 'Cu': 0.20, 'Co': 0.20, 'W': 0.15,
              'Mo': 0.06, 'V': 0.04, 'Nb': 0.03, 'Ti': 0.03, 'Al': 0.03, 'N': 0.03, 'B': 0.002}
REL_TOL = 0.10

# Bu değerin altındaki miktar aile kimliğine yazılmaz (kalıntı / iz element)
ANLAMLI = {e: t / 2 for e, t in MUTLAK_TOL.items()}


def alloy_part(nom):
    return {e: nom[e] for e in SIRA if nom.get(e, 0) >= ANLAMLI[e]}


def family_id(nom):
    a = alloy_part(nom)
    return '_'.join(f'{e}{a[e]:g}' for e in SIRA if e in a) or 'saf'


def close(a, b):
    for e in SIRA:
        x, y = a.get(e, 0.0), b.get(e, 0.0)
        if abs(x - y) > max(MUTLAK_TOL[e], REL_TOL * max(x, y)):
            return False
    return True


def cluster(items):
    """
    items: [(anahtar, nominal_bileşim)] öncelik sırasında.
    Dönüş: ({anahtar: aile_id}, {aile_id: (kurucu_anahtar, aile_bileşimi)})
    """
    aileler = {}    # id -> (kurucu, bileşim)
    atama = {}
    for k, nom in items:
        a = alloy_part(nom)
        for fid, (_, fa) in aileler.items():
            if close(a, fa):
                atama[k] = fid
                break
        else:
            fid = family_id(nom)
            if fid in aileler:          # yuvarlama aynı ada düşürdüyse (çok nadir) tekilleştir
                fid = f'{fid}#{len(aileler)}'
            aileler[fid] = (k, a)
            atama[k] = fid
    return atama, aileler
