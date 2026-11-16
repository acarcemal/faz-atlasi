"""
Veritabanını kaynaklardan baştan kurar (idempotent: her çalıştırmada tablolar silinip yeniden doldurulur).

Sıra ve öncelik (küçük = güvenilir; aynı çelik birden çok kaynakta varsa bileşim en güvenilirden gelir):
  10  hesap/celik_kutuphanesi.py   — 63 çelik, EN/ISO standart aralıkları (web'in kullandığı tek kaynak)
  10  paslanmaz.py                 — EN 10088 paslanmazları
  50  data/esdegerler.csv          — ek norm adları (JIS, UNS ...); satın alınan listeler --esdeger ile eklenir
  60  Mendeley 10.17632/jmwb9ddd43.1 — steel_database_3234.xlsx (AISI/ASTM/ACI, tek bileşim)
  70  Mendeley 10.17632/mfhvdv4b8z.1 — database_classification.csv (GOST, tek bileşim + mikroyapı sınıfı)

Tek çelik / çoklu norm: yeni kayıt, kesin (approx=0) ve kalite düzeyindeki (scope=grade) bir norm adı üzerinden
mevcut bir çeliğe denk geliyorsa yeni çelik açılmaz; ad ve kaynak mevcut çeliğe eklenir.
"""
import csv
import os
import sys

import pandas as pd

from ..db.models import (AlloyFamily, Base, DataSource, Steel, SteelComposition, SteelDesignation,
                         SteelSource)
from . import classify, families
from .designations import library_aisi, normalize, parse_dataset_name
from .paslanmaz import PASLANMAZLAR, nominal as pas_nominal

KOK = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
VERI = os.path.join(KOK, 'hesap', 'veri_kaynaklari')
XLSX = os.path.join(VERI, 'steel_database_3234.xlsx')
GOST_CSV = os.path.join(VERI, 'database_classification.csv')
ESDEGER_CSV = os.path.join(KOK, 'backend', 'data', 'esdegerler.csv')

KAYNAKLAR = [
    ('faz_atlasi_lib', 'Faz Atlası çelik kütüphanesi (hesap/celik_kutuphanesi.py)', 'EN/ISO standart döküm analizi aralıkları', 'MIT', 10),
    ('en10088', 'Paslanmaz çelikler (EN 10088-1/-3 aralıkları)', 'EN 10088-1, EN 10088-3', None, 10),
    ('esdeger', 'Norm eşdeğerleri (backend/data/esdegerler.csv)', None, None, 50),
    ('mendeley_3234', 'Steel database (3234 entries)', 'Mendeley Data, DOI 10.17632/jmwb9ddd43.1', None, 60),
    ('mendeley_gost', 'Steel classification database (GOST)', 'Mendeley Data, DOI 10.17632/mfhvdv4b8z.1', None, 70),
]

XLSX_ELEMENTLER = ['C', 'Mn', 'Si', 'Cr', 'Ni', 'Mo', 'V', 'Cu', 'Co', 'Nb', 'Ti', 'Al', 'N', 'B', 'Zr', 'P', 'S']
GOST_ELEMENTLER = ['C', 'Mn', 'Si', 'Cr', 'Ni', 'Mo', 'V', 'W', 'Cu', 'Co', 'Nb', 'Ti', 'Al', 'N', 'B', 'P', 'S', 'As']

# Bir ASTM şartnamesi altındaki satırlar bu kadar yakınsa aynı kalitedir (döküm farkı); uzaksa ayrı kalite
SARTNAME_TOL = 0.035


class Kurucu:
    def __init__(self, session, log=print):
        self.s = session
        self.log = log
        self.oncelik = {k[0]: k[4] for k in KAYNAKLAR}
        self.indeks = {}   # (sistem, code_norm) -> {steel_id: (approx, scope)}
        self.celik = {}    # id -> Steel
        self.uyari = []

    # --- yardımcılar
    def _ad_ekle(self, st, sistem, kod, kaynak, approx=False, scope='grade'):
        kn = normalize(kod, sistem)
        if not kn:
            return
        mevcut = self.indeks.setdefault((sistem, kn), {})
        if st.id in mevcut:
            # aynı ad zaten var; kesin bilgi yaklaşık bilginin önüne geçer
            if not approx and mevcut[st.id][0]:
                for d in st.designations:
                    if d.system == sistem and d.code_norm == kn:
                        d.approx = False
                mevcut[st.id] = (False, scope)
            return
        st.designations.append(SteelDesignation(system=sistem, code=kod, code_norm=kn, approx=approx,
                                                scope=scope, source_id=kaynak))
        mevcut[st.id] = (approx, scope)

    def bul(self, sistem, kod):
        """Kesin ve kalite düzeyinde eşleşen çelik (yoksa None)."""
        for sid, (approx, scope) in self.indeks.get((sistem, normalize(kod, sistem)), {}).items():
            if not approx and scope == 'grade':
                return self.celik[sid]
        return None

    def yeni(self, ad, grup, grup_en, sinif, sinif_kaynak, kaynak, kaynak_ref, bilesim,
             standart=None, kullanim=None, kullanim_en=None):
        """bilesim: element -> (min, max, nominal); min/max None olabilir."""
        st = Steel(standard_name=ad, group_name=grup, group_name_en=grup_en, steel_class=sinif,
                   class_source=sinif_kaynak, standard_code=standart, usage_tr=kullanim, usage_en=kullanim_en,
                   primary_source_id=kaynak)
        for e, (mn, mx, nom) in bilesim.items():
            st.composition.append(SteelComposition(element=e, min_val=mn, max_val=mx, nominal_val=nom))
        st.sources.append(SteelSource(source_id=kaynak, source_ref=kaynak_ref))
        self.s.add(st)
        self.s.flush()
        self.celik[st.id] = st
        return st

    def kaynak_ekle(self, st, kaynak, ref):
        if not any(x.source_id == kaynak and x.source_ref == ref for x in st.sources):
            st.sources.append(SteelSource(source_id=kaynak, source_ref=ref))

    def birlestir(self, tut, at):
        """`at` çeliğinin adlarını ve kaynaklarını `tut`a taşır, `at`ı siler. Bileşim `tut`ta kalır."""
        for d in list(at.designations):
            self.indeks[(d.system, d.code_norm)].pop(at.id, None)
            self._ad_ekle(tut, d.system, d.code, d.source_id, d.approx, d.scope)
        for x in at.sources:
            self.kaynak_ekle(tut, x.source_id, x.source_ref)
        del self.celik[at.id]
        self.s.delete(at)
        self.s.flush()

    def ya_birlestir_ya_ekle(self, adlar, kaynak, ref, olustur):
        """adlar: [(sistem, kod, scope)]. Kesin eşleşen çelik varsa ona ekler, yoksa olustur() ile açar."""
        hedef = next((h for si, k, sc in adlar if sc == 'grade' for h in [self.bul(si, k)] if h), None)
        st = hedef or olustur()
        if hedef:
            self.kaynak_ekle(hedef, kaynak, ref)
        for si, k, sc in adlar:
            self._ad_ekle(st, si, k, kaynak, scope=sc)
        return st, hedef is not None

    # --- kaynaklar
    def kutuphane(self):
        sys.path.insert(0, os.path.join(KOK, 'hesap'))
        import celik_kutuphanesi as k
        for ad, no, aisi, grup, std, kullanim, aralik in k.CELIKLER:
            nom = k.nominal(aralik)
            bil = {e: (a[0], a[1], nom[e]) for e, a in aralik.items()}
            st = self.yeni(ad, grup, k.GRUP_EN[grup], 'carbon_low_alloy', 'library', 'faz_atlasi_lib', ad, bil,
                           std, kullanim, k.KULLANIM_EN[ad])
            if not ad.startswith('AISI '):
                self._ad_ekle(st, 'EN', ad, 'faz_atlasi_lib')
            if no.strip() not in ('', '—'):
                self._ad_ekle(st, 'WNR', no, 'faz_atlasi_lib')
            for si, kod, approx in library_aisi(aisi):
                self._ad_ekle(st, si, kod, 'faz_atlasi_lib', approx)
        self.log(f'  kütüphane: {len(k.CELIKLER)} çelik')

    def paslanmaz(self):
        for ad, no, sinif, kul, kul_en, aralik, adlar in PASLANMAZLAR:
            nom = pas_nominal(aralik)
            bil = {e: (a[0], a[1], nom[e]) for e, a in aralik.items()}
            grup, grup_en = classify.group_for(sinif, nom)
            st = self.yeni(ad, grup, grup_en, sinif, 'library', 'en10088', ad, bil, 'EN 10088', kul, kul_en)
            self._ad_ekle(st, 'EN', ad, 'en10088')
            self._ad_ekle(st, 'WNR', no, 'en10088')
            for si, kod, approx in adlar:
                self._ad_ekle(st, si, kod, 'en10088', approx)
        self.log(f'  paslanmaz: {len(PASLANMAZLAR)} çelik')

    @staticmethod
    def _bilesim(seri, elementler):
        return {e: (None, None, round(float(seri[e]), 4)) for e in elementler if e in seri and float(seri[e]) > 0}

    def _veri_celigi(self, ad, nom_bil, kaynak, ref, adlar, dokum=False, sinif=None):
        nom = {e: v[2] for e, v in nom_bil.items()}
        if sinif:
            sinif_kaynak = 'dataset'
        else:
            sinif, sinif_kaynak = classify.heuristic(nom), 'heuristic'
        grup, grup_en = classify.group_for(sinif, nom, dokum)
        return self.ya_birlestir_ya_ekle(
            adlar, kaynak, ref, lambda: self.yeni(ad, grup, grup_en, sinif, sinif_kaynak, kaynak, ref, nom_bil))

    def mendeley_3234(self, yol=XLSX):
        df = pd.read_excel(yol)
        # dosyada '®' bozuk kodlanmış ('Â®')
        df['Name'] = df['Name'].astype(str).str.replace('Â', '').str.strip()
        yeni = birlesen = 0
        for ad, g in df.groupby('Name', sort=True):
            adlar = parse_dataset_name(ad)
            sartname = any(sc == 'specification' for _, _, sc in adlar)
            gruplar = _yakin_kumeler(g[XLSX_ELEMENTLER]) if sartname else [g[XLSX_ELEMENTLER]]
            bils = [self._bilesim(kume.median(), XLSX_ELEMENTLER) for kume in gruplar]
            imzalar = [_imza(b) for b in bils]
            imzalar = [f'{i} C{b["C"][2]:g}' if imzalar.count(i) > 1 and 'C' in b else i for i, b in zip(imzalar, bils)]
            for bil, imza in zip(bils, imzalar):
                gorunen = f'{ad} ({imza})' if len(gruplar) > 1 else ad
                _, b = self._veri_celigi(gorunen, bil, 'mendeley_3234', gorunen, adlar, dokum=ad.startswith('Cast'))
                birlesen += b
                yeni += not b
        self.log(f'  Mendeley 3234: {df.Name.nunique()} ad -> {yeni} yeni çelik, {birlesen} mevcut çeliğe bağlandı')

    def mendeley_gost(self, yol=GOST_CSV):
        df = pd.read_csv(yol, encoding_errors='replace')
        df['Name'] = df['Name'].astype(str).str.strip().str.replace('�', '-')
        df['_n'] = df['Name'].map(lambda x: normalize(x, 'GOST'))
        yeni = birlesen = 0
        for _, g in df.groupby('_n', sort=True):
            ad = g['Name'].iloc[0]
            bil = self._bilesim(g[GOST_ELEMENTLER].median(), GOST_ELEMENTLER)
            sinif = classify.from_dataset(g['Class'].mode().iloc[0], {e: v[2] for e, v in bil.items()})
            for diger in g['Name'].unique()[1:]:   # aynı kalitenin farklı yazımları (36X18N25C2 / 36X18N25S2)
                self.uyari.append(f'GOST yazım birleşti: {ad} = {diger}')
            _, b = self._veri_celigi(ad, bil, 'mendeley_gost', ad, [('GOST', ad, 'grade')], sinif=sinif)
            birlesen += b
            yeni += not b
        self.log(f'  Mendeley GOST: {df._n.nunique()} kalite -> {yeni} yeni çelik, {birlesen} mevcut çeliğe bağlandı')

    def esdegerler(self, yol, kaynak='esdeger'):
        n = birlesme = 0
        with open(yol, encoding='utf-8') as f:
            satirlar = [r for r in csv.DictReader(l for l in f if not l.startswith('#'))]
        for r in satirlar:
            capa = self.bul(r['anchor_system'], r['anchor_code'])
            if not capa:
                self.uyari.append(f'eşdeğer: çapa bulunamadı {r["anchor_system"]} {r["anchor_code"]}')
                continue
            approx = r['approx'].strip() in ('1', 'true', 'True')
            diger = None if approx else self.bul(r['system'], r['code'])
            if diger and diger.id != capa.id:
                tut, at = sorted([capa, diger], key=lambda c: (self.oncelik[c.primary_source_id], c.id))
                self.birlestir(tut, at)
                capa = tut
                birlesme += 1
            self._ad_ekle(capa, r['system'], r['code'], kaynak, approx)
            n += 1
        self.log(f'  eşdeğerler ({os.path.basename(yol)}): {n} ad, {birlesme} çelik birleştirildi')

    def aileler(self):
        sirali = sorted(self.celik.values(), key=lambda c: (self.oncelik[c.primary_source_id], c.id))
        atama, ailes = families.cluster([(c.id, c.nominal()) for c in sirali])
        for fid, (kurucu, bil) in ailes.items():
            self.s.add(AlloyFamily(id=fid, base_elements=bil, founder_steel_id=kurucu))
        self.s.flush()
        for c in sirali:
            c.alloy_family_id = atama[c.id]
        self.log(f'  aileler: {len(self.celik)} çelik -> {len(ailes)} alaşım ailesi (dikey kesit)')


def _imza(bil):
    """Bir şartnamedeki kaliteleri ayırt etmek için en yüksek iki alaşım elementi: 'Cr2.25 Mo1'."""
    al = sorted(((v[2], e) for e, v in bil.items() if e not in ('C', 'P', 'S', 'Si')), reverse=True)[:2]
    return ' '.join(f'{e}{v:g}' for v, e in al) or f'C{bil.get("C", (0, 0, 0))[2]:g}'


def _yakin_kumeler(df):
    kumeler = []
    for _, r in df.iterrows():
        for k in kumeler:
            if (k.iloc[0] - r).abs().max() <= SARTNAME_TOL:
                k.loc[len(k)] = r
                break
        else:
            kumeler.append(pd.DataFrame([r]).reset_index(drop=True))
    return kumeler


def _hesaplanmis_kesitler(engine, session):
    """Yeniden kurulumda saatler süren kesit hesapları kaybolmasın: aile kimliğine göre saklanır, sonra geri yazılır."""
    from sqlalchemy import inspect, select
    if not inspect(engine).has_table('alloy_families'):
        return {}
    satirlar = session.execute(select(AlloyFamily.id, AlloyFamily.isopleth_boundaries, AlloyFamily.calculated_at)
                               .where(AlloyFamily.isopleth_boundaries.is_not(None))).all()
    session.rollback()
    return {fid: (b, t) for fid, b, t in satirlar}


def build(engine, session, esdeger_dosyalari=(), log=print, xlsx=XLSX, gost=GOST_CSV):
    kesitler = _hesaplanmis_kesitler(engine, session)
    session.close()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    for kid, ad, atif, lisans, onc in KAYNAKLAR:
        session.add(DataSource(id=kid, name=ad, citation=atif, license=lisans, priority=onc))
    session.flush()
    k = Kurucu(session, log)
    k.kutuphane()
    k.paslanmaz()
    k.esdegerler(ESDEGER_CSV)
    k.mendeley_3234(xlsx)
    k.mendeley_gost(gost)
    for yol in esdeger_dosyalari:
        k.esdegerler(yol)
    k.aileler()
    korunan = 0
    for f in session.query(AlloyFamily).filter(AlloyFamily.id.in_(list(kesitler))):
        f.isopleth_boundaries, f.calculated_at = kesitler[f.id]
        korunan += 1
    if kesitler:
        log(f'  hesaplanmış kesitler: {korunan}/{len(kesitler)} korundu (kalanların ailesi artık yok)')
    session.commit()
    return k
