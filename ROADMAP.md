<!--
  © Clearview Geographic LLC -- All Rights Reserved | Est. 2018
  CVG SLR Wizard — ROADMAP
-->

# CVG SLR Wizard — Development Roadmap

> Version: v1.1.1 | Author: Alex Zelenski, GISP | Last updated: 2026-03-21 (Session 7) — GeoServer Raster & Vector integration section added

---

## ✅ v1.0.0 — Initial Framework (2026-03-19)

- [x] Core package structure: `__init__`, `config`, `paths`, `monitoring`
- [x] Raster I/O (`io.py`): read/write GeoTIFF, reproject, clip to AOI, raster-to-vector
- [x] NOAA TR-083 SLR projection table (`noaa.py`): All 6 scenarios × 2030–2100, 6 CONUS stations
- [x] NOAA VDatum integration (`vdatum.py`): local JAR + REST API fallback
- [x] Bathtub inundation processing engine (`processing.py`): queen/rook connectivity, min-depth filter
- [x] Checkpoint/resume system (`recovery.py`)
- [x] JSON + PDF report generation (`report.py`)
- [x] SLR analysis core (`core.py`): `project_slr()`, `run_slr_analysis()`, `run_sensitivity()`
- [x] Knowledge base (`insights.py`): 7 guidance topics
- [x] CLI (`cli.py`): `run`, `batch`, `web`, `insights`, `stations`, `project`, `new-config`
- [x] FastAPI REST API (`web_api.py`): 5 endpoints
- [x] Jinja2 web rendering (`web.py`)
- [x] Unit test suite: config, noaa, processing
- [x] Docker / docker-compose, .gitignore, README

---

## ✅ v1.1.0 — Standalone Hardening + Test Parity (2026-03-20)

- [x] Removed `storm-surge-wizard` dependency; fully standalone package
- [x] Full test parity: 232 tests passing (59 engine + 33 monitoring + 22 recovery + 24 report + 32 web_api)
- [x] NOAA TR-083 (Sweet et al. 2022) benchmark values validated in test suite
- [x] CVG File Authorship Requirement headers on all source files
- [x] `GET /api/wizards/status` cross-wizard discovery endpoint

## ✅ v1.1.1 — Docker Fix + Landing Page Genericization (2026-03-21)

- [x] `Dockerfile`: `requirements-lock.txt` → `requirements-web.txt` (fixed yanked `numpy==2.0.0rc1`)
- [x] `static/landing/slr-index.html`: removed Monroe County / client-specific content; CVG product-selling copy
- [x] Docker image rebuilt (1.74 GB, Python 3.13-slim); `cvg-slr` container restarted and verified healthy

## 🔜 v1.2.0 — Data & Station Expansion (formerly v1.1.0)

- [ ] Expand SLR table to all ~75 CONUS CO-OPS stations in NOAA TR-083 Appendix C
- [ ] Alaska, Hawaii, Pacific territories SLR scenarios (NOAA TR-083 regional appendices)
- [ ] NOAA CO-OPS live SLR trend API integration (observed vs. projected)
- [ ] Auto-detect nearest CO-OPS station from DEM bounding box centroid
- [ ] NOAA Digital Coast seamless DEM integration (auto-download for AOI)

---

## 🔜 v1.3.0 — Compound Flood Integration

- [ ] Compound flood module: SLR + storm surge WSE combination
- [ ] Interface with `storm_surge_wizard` for joint WSE inputs
- [ ] Interface with `rainfall_wizard` for blocked-outlet scenario
- [ ] Joint probability documentation and QA warnings
- [ ] Multi-hazard difference grid output (compound minus individual)

---

## 🔜 v1.4.0 — Enhanced Inundation Science

- [ ] Hydrodynamic connectivity filter using scipy `label` (already partial)
- [ ] Shoreline buffer seeding for coastal connectivity
- [ ] Multi-layer DEM support (buildings, bridges, levees masked)
- [ ] Vertical uncertainty propagation (DEM RMSE × SLR CI → depth uncertainty)
- [ ] FEMA freeboard adjustment layer

---

## 🔜 v1.5.0 — Web UI & Visualization

- [ ] Interactive Jinja2 / Leaflet map viewer for inundation extent
- [ ] Multi-scenario side-by-side comparison view
- [ ] Scenario slider (animated year progression)
- [ ] Export to KMZ / GeoJSON for Google Earth / ArcGIS Online
- [ ] Progress bar / streaming updates via WebSocket

---

## 🔜 v2.0.0 — Full GIS Automation

- [ ] ArcGIS toolbox wrapper (ArcPy integration)
- [ ] QGIS Processing plugin
- [ ] Batch scheduled runs (daily tide + SLR monitoring dashboard)
- [ ] NOAA CO-OPS WebSocket live tidal monitoring integration

---

## 🔜 v2.1.0 — GeoServer Raster & Vector Integration

> **Platform:** CVG GeoServer Raster (VM 454 · **raster.cleargeo.tech**) + GeoServer Vector (VM 455 · **vector.cleargeo.tech**)
> GeoServer 2.28.3 · Caddy 2-alpine TLS · Watchtower daily pull · NAS mounts `/mnt/cgps` + `/mnt/cgdp`

### Raster Integration (raster.cleargeo.tech — WMS/WCS/WMTS)

- [ ] **COG export**: after each `processing.py` inundation run, convert output GeoTIFF to COG:
  `gdal_translate -of COG inundation_{scenario}_{year}.tif /mnt/cgdp/cogs/slr/{project}/{scenario}_{year}.tif`
- [ ] Register COGs as ImageMosaic on `raster.cleargeo.tech` with WMS **TIME dimension**:
  layer `cvg:slr_{project}_{scenario}` — TIME values = `2030,2040,...,2100`
- [ ] `GET /api/layers/raster` endpoint in `web_api.py` — returns WMS GetCapabilities URL + TIME dimension values
- [ ] Leaflet map in `web.py`: animated scenario slider using `L.timeDimension` plugin consuming TIME-enabled WMS
  ```javascript
  // Animated year progression: 2030 → 2100 every 1s
  L.timeDimension({ period: "P10Y", ... })
  ```
- [ ] WMS SLD style per scenario: Intermediate Blue (2030–2060), Deep Blue (2070–2100), Red (Intermediate High/High)
- [ ] GeoWebCache WMTS tile seeding for all scenario × year combinations

### Vector Integration (vector.cleargeo.tech — WFS)

- [ ] **Scenario boundary export**: at end of each `run_slr_analysis()`, vectorize inundation extent
  (depth > 0) → GeoPackage: `/mnt/cgdp/vectors/slr/{project}/{scenario}_{year}_extent.gpkg`
- [ ] Register on Vector GeoServer as WFS layer: `cvg:slr_{project}_{scenario}_{year}_extent`
- [ ] **Shoreline buffer seeding layer**: export `shoreline_seed.gpkg` from `processing.py` as
  `cvg:slr_{project}_shoreline` WFS layer
- [ ] `GET /api/layers/vector` endpoint in `web_api.py` — returns WFS GetCapabilities URL + all extent layers
- [ ] `GetFeatureInfo` on map click: returns inundation depth + scenario name + year from both raster (WMS) and vector (WFS)

### Cross-Wizard Layer Registry

- [ ] `GET /api/platform/layers` — lists all active WMS/WCS/WFS layers across SSW, SLR, and Rainfall
  (consumed by future CVG unified map portal)

### Layer Naming Convention

| Layer Type | Pattern | Example |
|---|---|---|
| Inundation GeoTIFF mosaic (WMS) | `cvg:slr_{project}_{scenario}` | `cvg:slr_miami_int_high` |
| Inundation extent polygon (WFS) | `cvg:slr_{project}_{scenario}_{year}_extent` | `cvg:slr_miami_int_high_2060_extent` |
| Shoreline seed boundary (WFS) | `cvg:slr_{project}_shoreline` | `cvg:slr_miami_shoreline` |
| Tile cache (WMTS) | `cvg:gwc_slr_{project}_{scenario}` | `cvg:gwc_slr_miami_int_high` |

### Infrastructure Reference

| Service | VM | Hostname | Purpose |
|---|---|---|---|
| GeoServer Raster | VM 454 · 10.10.10.203 | raster.cleargeo.tech | WMS TIME-dim mosaic per scenario/year |
| GeoServer Vector | VM 455 · 10.10.10.204 | vector.cleargeo.tech | WFS inundation extent + shoreline seed |

---

*© Clearview Geographic LLC — Proprietary — All Rights Reserved*
