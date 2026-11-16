# Faz Atlası API. Depo kökünden kurulur (TDB hesap/tdb/ altında olmalı; README'deki adresten indirilir):
#   docker compose -f backend/docker-compose.yml up --build
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 \
    FAZ_TDB=/app/tdb/mc_fe_pycalphad.tdb

WORKDIR /app
COPY backend/requirements.txt backend/requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-api.txt

COPY hesap/tdb/mc_fe_pycalphad.tdb /app/tdb/
COPY hesap/celik_kutuphanesi.py /app/hesap/
COPY hesap/veri_kaynaklari /app/hesap/veri_kaynaklari
COPY backend /app/backend

RUN useradd --create-home faz && chown -R faz /app
USER faz
EXPOSE 8000
# pycalphad iş parçacığı güvenli değil ve her işlem kendi model önbelleğini tutar (~1 GB):
# ölçeklemek için worker sayısı yerine konteyner sayısı artırılır.
CMD ["uvicorn", "faz_atlasi.api.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
