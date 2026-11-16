"""
Faz Atlası REST API.

  .venv/Scripts/python -m uvicorn faz_atlasi.api.main:app --app-dir backend --port 8000
  Belgeler: http://localhost:8000/docs

Ortam değişkenleri: FAZ_DB_URL (varsayılan backend/data/faz_atlasi.db), FAZ_TDB, FAZ_PDENS,
FAZ_WARMUP=0 (açılışta TDB yüklenmesin), FAZ_CORS (virgülle ayrılmış kökenler).
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from ..calc import isil_islem
from ..calc.engine import get_engine
from ..calc.point import GecersizBilesim, PointService
from ..db import AlloyFamily, CalculationCache, Steel, make_engine
from ..library import classify
from ..library.search import search
from . import schemas

durum = {}


def _kalici_onbellek(Session):
    def oku(anahtar):
        with Session() as s:
            c = s.get(CalculationCache, anahtar)
            return c.result_data if c else None

    def yaz(anahtar, veri):
        with Session() as s:
            s.merge(CalculationCache(cache_key=anahtar, result_data=veri, created_at=datetime.utcnow()))
            s.commit()
    return oku, yaz


@asynccontextmanager
async def lifespan(app):
    db = make_engine()
    CalculationCache.__table__.create(db, checkfirst=True)
    durum['Session'] = sessionmaker(bind=db, expire_on_commit=False)
    motor = get_engine()
    if os.environ.get('FAZ_WARMUP', '1') != '0':
        # TDB okuma + en sık kullanılan sistemin (Fe-C-Mn-Si) derlenmesi açılışta yapılır
        PointService(motor).hesapla({'C': 0.4, 'Mn': 0.7, 'Si': 0.25}, 800)
    durum['point'] = PointService(motor, kalici=_kalici_onbellek(durum['Session']))
    yield
    db.dispose()


app = FastAPI(title='Faz Atlası API', version='2.0.0-dev', lifespan=lifespan,
              description='Çelik kütüphanesi, alaşım aileleri (dikey kesitler) ve tek nokta CALPHAD dengesi.')
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get('FAZ_CORS', '*').split(','),
                   allow_methods=['GET', 'POST'], allow_headers=['*'])


def oturum():
    with durum['Session']() as s:
        yield s


def _ad(d):
    return schemas.DesignationOut(system=d.system, code=d.code, approx=d.approx)


@app.get('/api/v1/health')
def health():
    m = get_engine()
    return {'status': 'ok', 'tdb': os.path.basename(m.tdb_yolu), 'tdb_sha': m.tdb_ozet,
            'elements': sorted(m.destekli), 'warm_systems': len(m._modeller)}


@app.get('/api/v1/steels', response_model=schemas.SteelList)
def steels(q: str = '', system: str | None = Query(None, description='EN, WNR, AISI, UNS, ASTM, ACI, JIS, GOST, BS, TRADE'),
           steel_class: str | None = None, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
           s=Depends(oturum)):
    sonuc = search(s, q, system=system, steel_class=steel_class, limit=offset + limit)
    hesapli = set(s.scalars(select(AlloyFamily.id).where(AlloyFamily.isopleth_boundaries.is_not(None))))
    items = [schemas.SteelSummary(
        id=r['steel'].id, name=r['display_name'], standard_name=r['steel'].standard_name, matched=_ad(r['matched']),
        group=r['steel'].group_name, group_en=r['steel'].group_name_en, steel_class=r['steel'].steel_class,
        alloy_family_id=r['steel'].alloy_family_id, isopleth_available=r['steel'].alloy_family_id in hesapli)
        for r in sonuc[offset:]]
    return schemas.SteelList(total=len(sonuc), items=items)


@app.get('/api/v1/steels/{steel_id}', response_model=schemas.SteelDetail)
def steel(steel_id: int, s=Depends(oturum)):
    c = s.get(Steel, steel_id)
    if not c:
        raise HTTPException(404, 'Çelik bulunamadı')
    adlar = {}
    for d in c.designations:
        adlar.setdefault(d.system, []).append(_ad(d))
    return schemas.SteelDetail(
        id=c.id, standard_name=c.standard_name, designations=adlar, group=c.group_name, group_en=c.group_name_en,
        steel_class=c.steel_class, class_source=c.class_source, standard_code=c.standard_code,
        usage_tr=c.usage_tr, usage_en=c.usage_en,
        composition=[schemas.CompositionOut(element=x.element, min=x.min_val, max=x.max_val, nominal=x.nominal_val)
                     for x in sorted(c.composition, key=lambda x: (x.element != 'C', x.element))],
        alloy_family_id=c.alloy_family_id,
        isopleth_available=bool(c.family and c.family.isopleth_boundaries),
        sources=sorted({x.source_id for x in c.sources}))


@app.get('/api/v1/families/{family_id}', response_model=schemas.FamilyOut)
def family(family_id: str, s=Depends(oturum)):
    f = s.get(AlloyFamily, family_id)
    if not f:
        raise HTTPException(404, 'Aile bulunamadı')
    n = s.scalar(select(func.count()).select_from(Steel).where(Steel.alloy_family_id == family_id))
    return schemas.FamilyOut(id=f.id, base_elements=f.base_elements, steel_count=n,
                             isopleth_available=f.isopleth_boundaries is not None,
                             calculated_at=f.calculated_at.isoformat() if f.calculated_at else None)


@app.get('/api/v1/isopleth/{family_id}')
def isopleth(family_id: str, s=Depends(oturum)):
    f = s.get(AlloyFamily, family_id)
    if not f:
        raise HTTPException(404, 'Aile bulunamadı')
    if f.isopleth_boundaries is None:
        raise HTTPException(404, 'Bu ailenin kesiti henüz hesaplanmadı (backend/trace_families.py)')
    return f.isopleth_boundaries


def _rejim(sinif, nom):
    anahtar = (sinif, tuple(sorted(nom.items())))
    onbellek = durum.setdefault('rejim', {})
    if anahtar not in onbellek:
        onbellek[anahtar] = isil_islem.rejim(sinif, nom, durum['point'])
    return onbellek[anahtar]


@app.get('/api/v1/steels/{steel_id}/heat-treatment')
def steel_heat_treatment(steel_id: int, s=Depends(oturum)):
    """Çelik sınıfına göre rejim: dönüşüm (Ae1/Ae3/Ms) ya da çözeltiye alma (hassaslaşma, sigma, Md30)."""
    c = s.get(Steel, steel_id)
    if not c:
        raise HTTPException(404, 'Çelik bulunamadı')
    return {'steel_id': c.id, 'standard_name': c.standard_name, **_rejim(c.steel_class, c.nominal())}


@app.post('/api/v1/heat-treatment')
def heat_treatment(req: schemas.HeatTreatmentRequest):
    """Kullanıcı bileşimi için rejim; sınıf verilmezse bileşimden kestirilir."""
    nom = {e.strip().capitalize(): v for e, v in req.composition.items() if v > 0}
    sinif = req.steel_class or classify.heuristic(nom)
    try:
        return {'steel_class_source': 'request' if req.steel_class else 'heuristic', **_rejim(sinif, nom)}
    except GecersizBilesim as e:
        raise HTTPException(422, str(e))


@app.post('/api/v1/equilibrium/point', response_model=schemas.PointResponse)
def equilibrium_point(req: schemas.PointRequest):
    try:
        return durum['point'].hesapla(req.composition, req.T)
    except GecersizBilesim as e:
        raise HTTPException(422, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


# Web arayüzü aynı sunucudan: http://localhost:8000/ (API yolları yukarıda tanımlı olduğu için önceliklidir)
WEB = os.environ.get('FAZ_WEB_DIR') or os.path.join(os.path.dirname(__file__), '..', '..', '..', 'web')
if os.path.isdir(WEB):
    app.mount('/', StaticFiles(directory=WEB, html=True), name='web')
