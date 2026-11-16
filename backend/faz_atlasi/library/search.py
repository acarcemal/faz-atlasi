"""
Akıllı arama: kullanıcı hangi normla yazarsa yazsın (42CrMo4, 1.7225, AISI 4140, SCM440, G41400) aynı çeliğe ulaşır.
`system` verilirse sonuçlar o normda listelenir (ör. JIS seçilince sadece JIS adı olan çelikler, JIS adıyla).

Sıralama: tam eşleşme > önek eşleşmesi > içerme; aynı derecede kesin (approx=0) adlar önce.
Not: PostgreSQL'de büyük veride içerme araması için code_norm'a pg_trgm GIN indeksi eklenmeli (Faz 2).
"""
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from ..db.models import Steel, SteelDesignation
from .designations import query_variants


def _derece(code_norm, varyantlar):
    if code_norm in varyantlar:
        return 0
    if any(code_norm.startswith(v) for v in varyantlar):
        return 1
    return 2


def search(session, q='', system=None, steel_class=None, limit=50):
    q = (q or '').strip()
    sorgu = select(SteelDesignation).join(Steel)
    if system:
        sorgu = sorgu.where(SteelDesignation.system == system)
    if steel_class:
        sorgu = sorgu.where(Steel.steel_class == steel_class)
    varyantlar = query_variants(q) if q else []
    if varyantlar:
        sorgu = sorgu.where(or_(*[SteelDesignation.code_norm.contains(v, autoescape=True) for v in varyantlar]))

    eslesmeler = {}
    for d in session.scalars(sorgu):
        anahtar = (_derece(d.code_norm, varyantlar) if varyantlar else 0, d.approx, len(d.code_norm))
        if d.steel_id not in eslesmeler or anahtar < eslesmeler[d.steel_id][0]:
            eslesmeler[d.steel_id] = (anahtar, d)

    sirali = sorted(eslesmeler.values(), key=lambda x: (x[0], x[1].code))[:limit]
    celikler = {s.id: s for s in session.scalars(
        select(Steel).where(Steel.id.in_([d.steel_id for _, d in sirali]))
        .options(selectinload(Steel.designations), selectinload(Steel.composition)))}
    return [{'steel': celikler[d.steel_id], 'matched': d, 'display_name': d.code if system else celikler[d.steel_id].standard_name}
            for _, d in sirali]


def designations_by_system(steel):
    """{'EN': ['42CrMo4'], 'WNR': ['1.7225'], 'AISI': ['4140'], 'JIS': ['≈SCM440'], ...}"""
    out = {}
    for d in steel.designations:
        out.setdefault(d.system, []).append(('≈' if d.approx else '') + d.code)
    return out
