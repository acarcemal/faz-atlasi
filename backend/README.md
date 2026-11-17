# Faz Atlası 2.0 — Backend & Calculation Engine

**English** · [Türkçe](README.tr.md)

FastAPI service and static-export pipeline for the 546-steel database (SQLite / PostgreSQL), alloy-family clustering, boundary-traced vertical sections (isopleths), and single-point CALPHAD equilibrium calculations.

## Local setup

```bash
.venv/Scripts/pip install -r backend/requirements.txt -r backend/requirements-api.txt
.venv/Scripts/python backend/build_db.py                      # builds backend/data/faz_atlasi.db
.venv/Scripts/python backend/trace_families.py --celik 42CrMo4 # traces one alloy family's isopleth
.venv/Scripts/python -m uvicorn faz_atlasi.api.main:app --app-dir backend --port 8000
```

Interactive API docs: `http://localhost:8000/docs`. Run tests: `.venv/Scripts/python -m pytest backend/tests -q`.

The adapted thermodynamic database (`hesap/tdb/mc_fe_pycalphad.tdb`) is generated from `mc_fe_v2062.tdb` using `hesap/tdb_temizle.py` (see the main [README](../README.md)).

## REST API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/steels?q=&system=&steel_class=&limit=&offset=` | Search across all standards (42CrMo4, 1.7225, 4140, SCM440, G41400); `system=JIS` lists designations in that standard |
| `GET /api/v1/steels/{id}` | Designations, composition ranges, steel class, alloy family, data sources |
| `GET /api/v1/families/{id}` | Family base composition, member count, isopleth status |
| `GET /api/v1/isopleth/{family_id}` | Calculated isopleth: row phase fields (`rows`) and boundary curves (`lines`) |
| `GET /api/v1/steels/{id}/heat-treatment` | Heat-treatment regime by steel class (see below) |
| `GET /api/v1/steels/{id}/family-fit` | Deviation between the steel's own critical temperatures and its family's isopleth |
| `POST /api/v1/heat-treatment` | `{"composition": {...}, "steel_class": null}` → regime for a custom composition (class inferred if omitted) |
| `POST /api/v1/equilibrium/point` | `{"composition": {"C": 0.42, "Cr": 1.05, ...}, "T": 760}` → phase fractions, carbon in each phase, phase compositions |

## Heat-treatment regimes (`faz_atlasi/calc/isil_islem.py`)

| Mode | Steel class | Returned values |
|---|---|---|
| `transformation` | Carbon / low-alloy, martensitic stainless | Ae1, Ae3, carbide solvus, δ-ferrite start (CALPHAD); hardening window Ae3 + 30–50 °C; Ms (Andrews) |
| `solution_annealing` | Austenitic stainless | A1/A3 hidden (`hide`); solution annealing 1050–1100 °C; sensitization 500–800 °C & risk level (low if C ≤ 0.03% or Ti ≥ 5C / Nb ≥ 10C); M₂₃C₆ and σ solvus (CALPHAD); Ms (Eichelman–Hull), Md30 (Angel) |
| `duplex` | Duplex stainless | Solution annealing 1020–1100 °C, σ solvus, 475 °C embrittlement range |
| `ferritic` | Ferritic stainless | Annealing 750–850 °C, 475 °C embrittlement range, σ solvus |
| `no_transformation` | Hadfield austenitic Mn, Fe–Ni, semi-austenitic | CALPHAD equilibrium transition temperatures only |

All CALPHAD transition temperatures are equilibrium values (not Ac/Ar), found by scanning 450–1350 °C in 50 °C steps followed by bisection to ±2 °C. First uncached evaluation takes 1–16 s (longer if a new component subset is compiled), then served from cache.

## Sub-families and steel–family fit (`calc/sapma.py`, `library/alt_aile.py`)

Each family isopleth is traced using the base alloy composition of the family's founding grade. When composition tolerances accumulate in the same direction, a member steel's critical temperatures can drift by 15–20 °C from the family section. Every steel is therefore checked against its family via CALPHAD at the steel's nominal carbon (Ae1, Ae3, carbide and σ solvus, δ-ferrite start to ±2 °C):

* **Deviation > 5 °C** (one row step of the isopleth) or a structural transition mismatch: the steel is separated from its parent family. It is first tested against other nearby families and newly created sub-families; if none fit within 5 °C, it forms a new **sub-family** (`alloy_families.parent_id` = original family).
* **Deviation ≤ 5 °C**: the steel stays in the family, and the web client shifts the temperature axis piecewise-linearly (`web/kesit.js: sicaklikEsle`) so critical lines match the steel's exact temperatures at its nominal carbon.
* Steels whose source record omits Mn or Si are flagged via `missing_elements` (treated as 0 in the calculation).

```bash
.venv/Scripts/python backend/split_families.py                       # measure deviations -> backend/data/alt_aileler.json
.venv/Scripts/python backend/split_families.py --uygula              # create sub-families and reassign steels
.venv/Scripts/python backend/trace_families.py --eksik --uyarlanir   # trace isopleths for the new sub-families
.venv/Scripts/python backend/export_static.py --hesap 4              # export static files for GitHub Pages / offline use
```

## Benchmarks (12-core laptop, 8 active workers)

| Operation | Measured time |
|---|---|
| Single point, cold start (TDB load + model compilation) | ~15 s (pre-warmed on startup via `FAZ_WARMUP`) |
| New component subset of the same alloy system (first call) | 2–5 s (compiled once, then kept in memory) |
| Single point, warm (42CrMo4, 5 components) | ~100–140 ms |
| Single point, warm (304, 6 components) | ~70–90 ms |
| Cached point | <1 ms |
| Isopleth boundary tracing (42CrMo4, 111 rows, 4 workers) | ~105 s, 4,800 points (vs. ~133 s, ~14,000 points for full grid) |

Boundary tracing reproduces the exact phase-field sequence of the full grid on 106 of 111 rows, with a median boundary difference of 0.001 wt% C (max 0.018 wt% C). The 5 differing rows involve four-phase slivers narrower than 0.01 wt% C.

## Known limitations

* `mc_fe_pycalphad.tdb` covers Fe, C, Cr, Cu, Mn, Mo, Ni, Si, V, and W. Elements outside the model (N, Ti, Nb, Al, Co, B) are excluded and reported in `ignored_elements`.
* `pycalphad` is not thread-safe in-process; concurrent requests are serialized with a lock (scale horizontally with multiple workers/containers).
