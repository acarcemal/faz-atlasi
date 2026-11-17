"""
Veritabanı şeması (SQLAlchemy 2). Aynı modeller SQLite ve PostgreSQL'de çalışır; JSON alanlar Postgres'te JSONB olur.

İlk plandaki (sabit norm sütunlu) şemadan farklar ve nedenleri:
  * Normlar (EN, W.Nr., AISI, UNS, JIS, GOST, ASTM ...) sabit sütunlar yerine `steel_designations` tablosunda.
    Böylece bir çeliğin istenen sayıda normu olur, yeni bir norm sistemi şema değişikliği gerektirmez ve
    arama tek indeksten yapılır. "Tek çelik / çoklu norm" kuralı: aynı çelik tek `steels` satırıdır.
  * `approx` bayrağı: "≈" karşılıklar (ör. 42CrMo4 ≈ SCM440) aynı çelik değildir; aranınca bulunur ama
    birleştirme (merge) için kullanılmaz.
  * Bileşimde min/max boş olabilir: açık veri setleri (Mendeley) aralık değil tek bileşim verir.
  * Her kayıt kaynağına bağlı (`data_sources`, `steel_sources`): hangi verinin nereden geldiği izlenebilir.
  * `steel_class`: mikroyapı sınıfı (östenitik paslanmaz vb.); Faz 3'teki ısıl işlem modu buna göre seçilir.
"""
from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JsonTip = JSON().with_variant(JSONB(), 'postgresql')

# Mikroyapı sınıfları (steels.steel_class)
SINIFLAR = (
    'carbon_low_alloy',           # ferrit-perlit / beynit / martenzit; A1-A3 dönüşümü olan çelikler
    'martensitic_stainless',      # 1.4021, 1.4034, 440B; Fe-Cr-C, A1 bandı var
    'ferritic_stainless',         # 1.4016 (430)
    'austenitic_stainless',       # 304, 316, 321; A1/A3 yok
    'duplex_stainless',           # 2205
    'semi_austenitic_stainless',  # östenit + martenzit (GOST AM sınıfı)
    'austenitic_other',           # Hadfield (yüksek Mn) gibi paslanmaz olmayan östenitikler
    'fe_ni_alloy',                # Fe-Ni (Invar türü, GOST XN35VT ...)
)


class Base(DeclarativeBase):
    pass


class DataSource(Base):
    __tablename__ = 'data_sources'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    citation: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(String(128))
    priority: Mapped[int] = mapped_column(Integer, default=100)  # küçük = güvenilir; birleştirmede bileşim bundan alınır


class AlloyFamily(Base):
    """Hesaplanan dikey kesit. Karbon kesit ekseni olduğu için aile = karbon dışındaki alaşım bileşimi."""
    __tablename__ = 'alloy_families'
    id: Mapped[str] = mapped_column(String(128), primary_key=True)  # 'Mn0.75_Si0.25_Cr1.05_Mo0.225' / 'saf'
    base_elements: Mapped[dict] = mapped_column(JsonTip)               # {"Mn": 0.75, "Cr": 1.05, ...} ağ.%
    founder_steel_id: Mapped[int | None] = mapped_column(Integer)      # ailenin bileşimini veren çelik
    isopleth_boundaries: Mapped[dict | None] = mapped_column(JsonTip)  # Faz 2: sınır izleme çıktısı
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime)   # hesaplanmadıysa boş
    # alt aile ise ayrıldığı aile (library/alt_aile.py): üyesi ölçülen sapmayla o aileden çıkmış çelikler
    parent_id: Mapped[str | None] = mapped_column(String(128))

    steels: Mapped[list['Steel']] = relationship(back_populates='family')


class Steel(Base):
    __tablename__ = 'steels'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    standard_name: Mapped[str] = mapped_column(String(128))            # görünen ana ad: '42CrMo4', 'X5CrNi18-10'
    group_name: Mapped[str] = mapped_column(String(64))                # 'Islah çeliği', 'Östenitik paslanmaz'
    group_name_en: Mapped[str] = mapped_column(String(64))
    steel_class: Mapped[str] = mapped_column(String(32), index=True)  # SINIFLAR
    class_source: Mapped[str] = mapped_column(String(16))              # 'library' | 'dataset' | 'heuristic'
    standard_code: Mapped[str | None] = mapped_column(String(64))      # 'EN ISO 683-2'
    usage_tr: Mapped[str | None] = mapped_column(Text)
    usage_en: Mapped[str | None] = mapped_column(Text)
    alloy_family_id: Mapped[str | None] = mapped_column(ForeignKey('alloy_families.id'), index=True)
    primary_source_id: Mapped[str] = mapped_column(ForeignKey('data_sources.id'))

    family: Mapped[AlloyFamily | None] = relationship(back_populates='steels')
    designations: Mapped[list['SteelDesignation']] = relationship(
        back_populates='steel', cascade='all, delete-orphan', order_by='SteelDesignation.id')
    composition: Mapped[list['SteelComposition']] = relationship(
        back_populates='steel', cascade='all, delete-orphan')
    sources: Mapped[list['SteelSource']] = relationship(cascade='all, delete-orphan')

    def nominal(self):
        return {c.element: c.nominal_val for c in self.composition}


class SteelDesignation(Base):
    """Bir çeliğin bir norm sistemindeki adı. code_norm aramada kullanılan sadeleştirilmiş biçimdir."""
    __tablename__ = 'steel_designations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    steel_id: Mapped[int] = mapped_column(ForeignKey('steels.id', ondelete='CASCADE'))
    system: Mapped[str] = mapped_column(String(16))     # EN, WNR, AISI, UNS, ASTM, ACI, JIS, GOST, BS, TRADE
    code: Mapped[str] = mapped_column(String(128))      # görünen biçim: '1.7225', 'SCM440', '12X18N10T'
    code_norm: Mapped[str] = mapped_column(String(128))
    approx: Mapped[bool] = mapped_column(Boolean, default=False)
    scope: Mapped[str] = mapped_column(String(16), default='grade')  # 'grade' | 'specification' (ASTM A387 gibi)
    source_id: Mapped[str] = mapped_column(ForeignKey('data_sources.id'))

    steel: Mapped[Steel] = relationship(back_populates='designations')

    __table_args__ = (
        UniqueConstraint('steel_id', 'system', 'code_norm'),
        Index('ix_designation_norm', 'code_norm'),
        Index('ix_designation_system_norm', 'system', 'code_norm'),
    )


class SteelComposition(Base):
    __tablename__ = 'steel_compositions'
    steel_id: Mapped[int] = mapped_column(ForeignKey('steels.id', ondelete='CASCADE'), primary_key=True)
    element: Mapped[str] = mapped_column(String(4), primary_key=True)
    min_val: Mapped[float | None] = mapped_column(Float)
    max_val: Mapped[float | None] = mapped_column(Float)
    nominal_val: Mapped[float] = mapped_column(Float)

    steel: Mapped[Steel] = relationship(back_populates='composition')


class SteelSource(Base):
    """Çeliğin hangi kaynak(lar)da hangi adla geçtiği (birleştirilen kayıtlar dahil)."""
    __tablename__ = 'steel_sources'
    steel_id: Mapped[int] = mapped_column(ForeignKey('steels.id', ondelete='CASCADE'), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('data_sources.id'), primary_key=True)
    source_ref: Mapped[str] = mapped_column(String(256), primary_key=True)


class SteelFamilyFit(Base):
    """Çeliğin kritik sıcaklıklarının ailesinin kesitindekilerden farkı (calc/sapma.py). Arayüz bununla kesiti
    çeliğe göre düzeltir; ESIK'i aşan çelikler alt aileye ayrılır."""
    __tablename__ = 'steel_family_fit'
    steel_id: Mapped[int] = mapped_column(ForeignKey('steels.id', ondelete='CASCADE'), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(128))   # ölçümün yapıldığı aile; çelik taşınırsa geçersiz
    data: Mapped[dict] = mapped_column(JsonTip)           # sapma.olc çıktısı
    max_abs_delta: Mapped[float] = mapped_column(Float)
    within: Mapped[bool] = mapped_column(Boolean)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CalculationCache(Base):
    __tablename__ = 'calculation_cache'
    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA256(bileşim + T + P + tdb sürümü)
    result_data: Mapped[dict] = mapped_column(JsonTip)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
