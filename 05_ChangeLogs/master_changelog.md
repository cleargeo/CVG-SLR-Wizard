# CVG SLR Wizard — Master Changelog

> © Clearview Geographic LLC | Author: Alex Zelenski, GISP

All notable changes to the CVG SLR Wizard are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

*(Future changes go here before release)*

---

## [2026-03-21] – Session 6 – Production Deployment Verification

**ChangeID:** `20260321-AZ-Deploy-Session6`

**Scope:** Deployment verification — no application code changes.

**Verified:**

| Endpoint | Status | Version |
|---|---|---|
| https://slr.cleargeo.tech/health | ✅ 200 OK | v1.1.0 |

- `cvg-slr` Docker container on VM 451 (cvg-stormsurge-01, 10.10.10.200) confirmed healthy
- Serving correctly through Caddy reverse proxy on `cvg_net` Docker network
- All three CVG wizard applications verified live as part of platform health check

**Author:** Alex Zelenski, GISP  
**Approved by:** Alex Zelenski  
**Status:** ✅ Production

---

## [1.0.0] — 2026-03-19

**ChangeID**: `20260319-AZ-v1.0.0`
**Author**: Alex Zelenski, GISP

### Added
- Initial framework release of CVG SLR Wizard
- `slr_wizard` Python package with 13 modules
- **NOAA TR-083 SLR projection table** (`noaa.py`): All 6 scenarios (Low → Extreme), years 2030–2100, 6 CONUS CO-OPS stations with national-average fallback; linear interpolation for off-decade years
- **NOAA VDatum integration** (`vdatum.py`): local JAR v4.5.1 (preferred) + REST API fallback for tidal datum transformations (MLLW/MSL/MHW ↔ NAVD88)
- **Bathtub inundation engine** (`processing.py`): Queen/rook hydrological connectivity filter, minimum depth threshold, DEM unit auto-detection (m → ft), `run_batch()` for all scenarios × batch years
- **SLR analysis core** (`core.py`): `project_slr()`, `run_slr_analysis()`, `run_sensitivity()` with full NOAA TR-083 provenance metadata
- **Configuration system** (`config.py`): `SLRWizardConfig` dataclass with validation; JSON save/load; 6 validated sub-configs
- **Checkpoint/resume** (`recovery.py`): 9-stage pipeline checkpointing, JSON persistence, `build_cache_key()`
- **JSON + PDF reports** (`report.py`): structured report schema v1.0.0; `reportlab` PDF with tables
- **Knowledge base** (`insights.py`): 7 guidance topics covering NOAA scenarios, datum considerations, bathtub model limitations, FEMA context, uncertainty, compound flooding, adaptation strategies
- **CLI** (`cli.py`): `slr-wizard run|batch|web|insights|stations|project|new-config`; colour summary output
- **FastAPI REST API** (`web_api.py`): GET `/`, `/api/stations`, `/api/project`, `/api/insights[/{topic}]`; POST `/api/run`
- **Jinja2 web rendering** (`web.py`): `render_template()`, `render_index()`, `render_result()`, `render_error()`
- **Raster I/O** (`io.py`): `RasterData`, `read_raster`, `write_raster`, `reproject_to_match`, `clip_to_aoi`, `raster_to_vector`
- **Monitoring** (`monitoring.py`): `PerformanceTracker`, `ResourceSnapshot`, `timed_stage()` context manager
- **Paths** (`paths.py`): `get_output_dir`, `get_raster_path`, `get_report_path`, `resolve_vdatum_jar`
- Unit test suite: `test_config.py` (13 tests), `test_noaa.py` (12 tests), `test_processing.py` (7 tests)
- Docker image, docker-compose, `.gitignore`, `pytest.ini`, `requirements-lock.txt`
- `README.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE.md`

### References
- Sweet, W.V. et al. (2022). NOAA TR-083 Global and Regional Sea Level Rise Scenarios for the United States.


---

## [2026-03-20] – v1.1.0 – Standalone Hardening + Full Test Parity

**ChangeID:** `20260320-AZ-v1.1.0`

**Modified Files:**

| File | Change Summary |
|---|---|
| `pyproject.toml` | Removed `storm-surge-wizard>=1.4.1` dependency; version 1.0.0->1.1.0; added fastapi, uvicorn, rasterio, numpy, fiona, psutil to required deps |
| `slr_wizard/__init__.py` | Fixed stale docstring referencing SSW; updated to reflect standalone status |
| `slr_wizard/web_api.py` | Added `GET /api/wizards/status` endpoint for cross-wizard discovery |
| `tests/test_engine.py` | NEW: 59 tests covering NOAA TR-083 benchmarks, keyword-only API, interpolation, alias resolution, zero-dependency check |
| `tests/test_monitoring.py` | NEW: 33 tests covering ResourceSnapshot, take_snapshot, PerformanceTracker, timed_stage |
| `tests/test_recovery.py` | NEW: 22 tests covering Stage enum, CheckpointManager, build_cache_key |
| `tests/test_report.py` | NEW: 24 tests covering build_json_report, write_json_report, metadata |
| `tests/test_web_api.py` | NEW: 32 tests covering all API endpoints including /api/wizards/status |
| `05_ChangeLogs/master_changelog.md` | Added v1.1.0 entry |

**Summary:**

- SLR Wizard is now fully standalone (zero storm_surge_wizard dependency)
- All NOAA TR-083 (Sweet et al. 2022) benchmark values validated in test suite
- 232 total tests passing (was 121 before this release)
- Full header compliance with CVG File Authorship Requirement

**Tests:** 232 passed

**Approved By:** Alex Zelenski, GISP  
**Review Status:** Internal — Production Ready

---

## [2026-03-21] – v1.1.1 – Docker Build Fix + Landing Page Genericization

**ChangeID:** `20260321-AZ-v1.1.1`

**Modified Files:**

| File | Change Summary |
|---|---|
| `Dockerfile` | `requirements-lock.txt` → `requirements-web.txt` — eliminates yanked `numpy==2.0.0rc1` RC build failure via rasterio build dependency; web API requires only `fastapi`, `uvicorn`, `pydantic`, `reportlab`, `numpy>=1.26.0` (no GDAL/rasterio). Applied on VM 451 + locally (G: drive) |
| `requirements-web.txt` | Verified: `fastapi>=0.111.0`, `uvicorn[standard]>=0.29.0`, `pydantic>=2.8.0`, `python-multipart>=0.0.9`, `jinja2>=3.1.0`, `httpx>=0.27.0`, `click>=8.1.0`, `psutil>=5.9.0`, `reportlab>=4.1.0`, `numpy>=1.26.0` |
| `static/landing/slr-index.html` | Removed all Monroe County / Key West / EPSG:6437 / client-specific content; replaced with generic CVG product-selling copy — hero "Sea Level Rise Inundation Projections for Any Coastal Jurisdiction", GISP trust strip (4.9★, 49+ assessments, $2.5M+), 5 NOAA SLR scenarios × 4 horizon years (2030/2050/2075/2100) feature table, pricing `$3,500–$15,000`, FEMA BRIC/HMGP grant hook, `services@clearviewgeographic.com` CTA, DeLand FL footer, `cleargeo.tech/products.html` |
| `05_ChangeLogs/master_changelog.md` | Added this entry |
| `05_ChangeLogs/version_manifest.yml` | Bumped `current_version` to 1.1.1; added v1.1.1 release entry |
| `README.md` | Version header + badge bumped to v1.1.1 |

**Deployment:**

- `cvg-slr-wizard:latest` Docker image rebuilt on VM 451 (1.74 GB, Python 3.13-slim)
- `cvg-slr` container restarted and verified healthy ✅ (Up 32 min at verification)
- Landing page deployed: `/opt/cvg-platform/static/landing/slr/index.html` (32,105 bytes)
- Verified: 0 Monroe County / Key West / EPSG:6437 references (grep)

**Author:** Alex Zelenski, GISP  
**Approved by:** Alex Zelenski  
**Status:** ✅ Production
