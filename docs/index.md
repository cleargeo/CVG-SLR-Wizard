# CVG SLR Wizard — Documentation

> © Clearview Geographic LLC | Author: Alex Zelenski, GISP | v1.0.0

---

## Overview

The CVG SLR Wizard is a Python toolkit for generating sea level rise (SLR)
inundation depth grids from a DEM + NOAA TR-083 projections + NOAA VDatum datum shifts.

---

## Module Reference

### `slr_wizard.config`
Configuration dataclasses. All user-facing parameters.

| Class | Description |
|---|---|
| `SLRWizardConfig` | Root config object |
| `InputsConfig` | DEM path, NOAA station, custom offset |
| `SLRProjectionConfig` | Scenario, year, baseline datum, VDatum options |
| `ProcessingConfig` | Bathtub options, batch years, connectivity |
| `OutputConfig` | Output dir/prefix, write flags, compress |
| `RunMetadata` | Project name, analyst, notes |

Key functions: `load_config()`, `save_config()`, `validate_config()`

---

### `slr_wizard.noaa`
NOAA TR-083 SLR projection tables and CO-OPS station metadata.

| Function | Description |
|---|---|
| `get_slr_projection(scenario, year, station_id)` | Single SLR offset in feet |
| `get_all_scenarios_for_year(year, station_id)` | All 6 scenarios for a year |
| `list_supported_stations()` | Stations with embedded RSLR tables |
| `fetch_station_info(station_id)` | Live CO-OPS metadata fetch |

**Stations with embedded tables**: Key West (8724580), Mayport (8720218),
Charleston (8665530), Norfolk (8638610), Galveston (8771341), Grand Isle (8761724)

---

### `slr_wizard.vdatum`
NOAA VDatum tidal datum transformations.

| Function | Description |
|---|---|
| `get_datum_separation(lat, lon, from, to)` | Vertical separation in feet |
| `get_mllw_navd88_shift(lat, lon)` | MLLW → NAVD88 convenience |
| `get_msl_navd88_shift(lat, lon)` | MSL → NAVD88 convenience |
| `query_vdatum_local(...)` | Local JAR query |
| `query_vdatum_api(...)` | REST API query |

---

### `slr_wizard.processing`
Bathtub inundation model.

| Function | Description |
|---|---|
| `run_inundation(config)` | Single scenario/year run |
| `run_batch(config)` | Multi-scenario × multi-year batch |
| `InundationResult` | Output result dataclass |

**Pipeline stages**: `load_dem` → `clip_aoi` → `datum_shift` → `slr_offset` →
`inundation` → `write_outputs` → `vectorise` → `report`

---

### `slr_wizard.core`
High-level SLR analysis helpers (wraps `processing` and `noaa`).

| Function | Description |
|---|---|
| `project_slr(station_id, scenario, year)` | Returns `(slr_m, metadata)` |
| `run_slr_analysis(config)` | Full analysis → `SLRResult` |
| `run_sensitivity(station_id, year)` | All 6 scenarios → dict |

---

### `slr_wizard.report`
JSON and PDF report generation.

```python
from slr_wizard.report import write_reports
paths = write_reports(result, config, output_dir="output")
# paths: {"json": "output/...", "pdf": "output/..."}
```

---

### `slr_wizard.insights`
Knowledge base search.

```python
from slr_wizard.insights import search_insights, get_guidance
entries = search_insights("compound flood")
entry = get_guidance("scenarios")
```

---

## CLI Reference

```
slr-wizard run     --config CONFIG [--resume]
slr-wizard batch   --config CONFIG
slr-wizard web     [--host HOST] [--port PORT]
slr-wizard insights [QUERY...]
slr-wizard stations
slr-wizard project  --year YEAR [--station STATION_ID]
slr-wizard new-config [--output PATH]
```

---

## REST API Reference

Base URL: `http://localhost:8010`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/api/stations` | Supported CO-OPS stations |
| GET | `/api/project?year=2070&scenario=intermediate` | SLR projection |
| POST | `/api/run` | Full inundation analysis |
| GET | `/api/insights?q=datum` | Knowledge base search |
| GET | `/api/insights/{topic}` | Single topic |

Interactive docs: http://localhost:8010/docs

---

## NOAA TR-083 Scenarios

| ID | Name | 2050 (ft) | 2100 (ft) |
|---|---|---|---|
| `low` | Low | 0.5 | 1.6 |
| `intermediate_low` | Intermediate-Low | 0.7 | 2.5 |
| `intermediate` | **Intermediate** | **1.0** | **3.8** |
| `intermediate_high` | Intermediate-High | 1.3 | 5.5 |
| `high` | High | 1.6 | 7.3 |
| `extreme` | Extreme | 2.0 | 12.1 |

*National averages. Station-specific RSLR varies significantly.*

---

*© Clearview Geographic LLC — Proprietary — All Rights Reserved*
