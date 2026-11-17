"""
Alt aileler: aileleri ölçülen sapmaya göre bölme.

Bileşim toleransıyla kurulan aileler (families.py) çoğu çelik için yeterli; ama tolerans içindeki farklar aynı yöne
toplanınca iki çeliğin kritik sıcaklıkları 15–20 °C ayrışabiliyor (ör. Si'si verilmemiş ASTM çelikleri). Burada her
çelik ailesine karşı CALPHAD ile ölçülür (calc/sapma.py):
  * fark ≤ ESIK: çelik ailesinde kalır; kalan fark arayüzde düzeltilir.
  * fark > ESIK: bileşimce yakın başka bir mevcut aileye, sonra bu ailenin bu turda açılmış alt ailelerine
    ölçülür; hiçbirine uymazsa kendi bileşimiyle yeni bir alt aile kurar (kurucu o çelik, üst aile = eski aile).
Çelikler ailede kaynak önceliği sırasıyla gezilir (families.cluster ile aynı), sonuç belirlenimcidir.

Kararlar backend/data/alt_aileler.json'a yazılır (backend/split_families.py). build.py veritabanını baştan
kurarken bu dosyayı uygular; böylece saatler süren ölçüm yeniden kurulumda kaybolmaz.
"""
import json
import os

from . import families

KAYIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'alt_aileler.json')


def alasim(nom):
    """Alt aile bileşimi: çeliğin hesaba giren bütün alaşım elementleri (iz elementler de; kurucu kendi
    kesitine tam uysun diye families.alloy_part'taki eşik uygulanmaz)."""
    return {e: nom[e] for e in families.SIRA if nom.get(e, 0) > 0}


def _uzaklik(a, b):
    return sum(abs(a.get(e, 0) - b.get(e, 0)) / families.MUTLAK_TOL[e] for e in families.SIRA)


def ayir(aile_id, aile_alasim, uyeler, olc, adaylar=(), kullanilan=()):
    """
    uyeler: [(anahtar, nominal)] öncelik sırasında (kurucu dahil). olc(nominal, alaşım) -> sapma.olc sonucu.
    adaylar: [(aile_id, alaşım)] başka mevcut aileler; sadece bileşimce yakın olanlar (families.close) denenir.
    kullanilan: çakışmaması gereken aile kimlikleri.
    Dönüş: (atama {anahtar: aile_id}, olcumler {anahtar: ölçüm}, yeni {aile_id: (kurucu_anahtar, alaşım, üst)})
    """
    atama, olcumler, yeni = {}, {}, {}
    kullanilan = set(kullanilan) | {aile_id}
    for k, nom in uyeler:
        if not nom.get('C'):
            # kaynakta karbonu verilmemiş çelik (kesitte karbon eksendir): ölçülemez, ailesinde kalır
            atama[k], olcumler[k] = aile_id, None
            continue
        o = olc(nom, aile_alasim)
        if o['within']:
            atama[k], olcumler[k] = aile_id, o
            continue
        a = families.alloy_part(nom)
        yakin = [d for d in adaylar if d[0] != aile_id] + [(fid, b) for fid, (_, b, _) in yeni.items()]
        yakin = sorted((d for d in yakin if families.close(a, d[1])), key=lambda d: _uzaklik(a, d[1]))
        # ayrılan çeliğin eski ailesine farkı da saklanır (neden ayrıldığı görünsün)
        ust = {'family_id': aile_id, **{x: o[x] for x in ('pairs', 'mismatch', 'max_abs_delta')}}
        for fid, b in yakin:
            o2 = olc(nom, b)
            if o2['within']:
                atama[k], olcumler[k] = fid, {**o2, 'parent_fit': ust}
                break
        else:
            temel = families.family_id(nom)
            fid, n = temel, 2
            while fid in kullanilan:
                fid, n = f'{temel}~{n}', n + 1
            kullanilan.add(fid)
            b = alasim(nom)
            yeni[fid] = (k, b, aile_id)
            atama[k] = fid
            olcumler[k] = {**olc(nom, b), 'parent_fit': ust}
    return atama, olcumler, yeni


def celik_anahtari(st):
    """Yeniden kurulumda da aynı kalan çelik kimliği (veritabanı id'si değişebilir)."""
    return f'{st.primary_source_id}|{st.standard_name}'


def kayit_oku(yol=KAYIT):
    if not os.path.exists(yol):
        return {'meta': {}, 'families': {}, 'subfamilies': {}, 'steels': {}}
    with open(yol, encoding='utf-8') as f:
        return json.load(f)


def kayit_yaz(kayit, yol=KAYIT):
    gecici = yol + '.tmp'
    with open(gecici, 'w', encoding='utf-8') as f:
        json.dump(kayit, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(gecici, yol)


def uygula(session, kayit, log=print):
    """
    Kayıttaki alt aileleri ve ölçümleri veritabanına işler. Sadece ölçümün yapıldığı aile yapısı hâlâ geçerliyse
    (üst ailenin bileşimi aynı, çelik hâlâ o ailede ya da zaten alt ailesinde) uygulanır; değilse atlanır ve
    bildirilir (split_families.py yeniden çalıştırılmalı).
    Dönüş: (taşınan çelik sayısı, eklenen alt aile sayısı, atlanan kayıt sayısı)
    """
    from ..db.models import AlloyFamily, Steel, SteelFamilyFit
    celikler = {celik_anahtari(c): c for c in session.query(Steel)}
    gecerli_ust = {pid for pid, f in kayit['families'].items()
                   if (a := session.get(AlloyFamily, pid)) is not None and a.base_elements == f['base']}
    eklenen = atlanan = tasinan = 0
    for fid, sf in kayit['subfamilies'].items():
        kurucu = celikler.get(sf['founder'])
        if sf['parent'] not in gecerli_ust or kurucu is None:
            atlanan += 1
            continue
        if session.get(AlloyFamily, fid) is None:
            session.add(AlloyFamily(id=fid, base_elements=sf['base'], founder_steel_id=kurucu.id,
                                    parent_id=sf['parent']))
            eklenen += 1
    session.flush()
    for k, r in kayit['steels'].items():
        c = celikler.get(k)
        hedef = session.get(AlloyFamily, r['family'])
        if c is None or r['parent'] not in gecerli_ust or c.alloy_family_id not in (r['parent'], r['family']) \
                or hedef is None or hedef.base_elements != r['family_base']:
            atlanan += 1
            continue
        if c.alloy_family_id != r['family']:
            c.alloy_family_id = r['family']
            tasinan += 1
        session.merge(SteelFamilyFit(steel_id=c.id, family_id=r['family'], data=r['fit'],
                                     max_abs_delta=r['fit']['max_abs_delta'], within=r['fit']['within']))
    session.flush()
    if atlanan:
        log(f'  alt aileler: {atlanan} kayıt atlandı (aile yapısı ölçümden sonra değişmiş; split_families.py yeniden)')
    return tasinan, eklenen, atlanan


def bos_aileleri_sil(session):
    """Üyesi kalmamış ve kesiti henüz hesaplanmamış aileler (gereksiz hesap yapılmasın)."""
    from ..db.models import AlloyFamily, Steel
    dolu = {fid for (fid,) in session.query(Steel.alloy_family_id).distinct()}
    bos = [f for f in session.query(AlloyFamily) if f.id not in dolu and f.isopleth_boundaries is None]
    for f in bos:
        session.delete(f)
    session.flush()
    return len(bos)
