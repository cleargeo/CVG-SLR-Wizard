# CVG SLR Wizard — API Reference

> © Clearview Geographic LLC | Internal Use Only | CVG-ADF

Port: **8010** | Base URL: `http://localhost:8010` (dev) / `https://slr.cleargeo.tech` (prod)

---

## Overview

The SLR Wizard exposes a FastAPI REST API for NOAA TR-083 sea-level rise projections and
bathtub inundation analysis. All endpoints return JSON. The OpenAPI docs are available at
`/docs` (Swagger UI) and `/redoc`.

---

## Authentication

Internal use only — no API key required on the local network.
Production deployments behind Caddy require mutual TLS or network-level access control.

---

## Endpoints

### `GET /`

Health check.

**Response 200:**
```json
{
  "service": "CVG SLR Wizard",
  "version": "1.0.0",
  "status": "ok"
}
```

---

### `POST /slr`

Run a sea-level rise projection.

**Request body** (`application/json`):

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `station_id` | str | ✅ | — | NOAA CO-OPS station ID (e.g. `"8724580"`) |
| `scenario` | str | ✅ | — | NOAA TR-083 scenario: `Low`, `Intermediate-Low`, `Intermediate`, `Intermediate-High`, `High`, `Extreme` |
| `target_year` | int | ✅ | — | Projection year (2025–2150) |
| `baseline_year` | int | ❌ | `2000` | Baseline epoch year |
| `include_tidal_datums` | bool | ❌ | `false` | Include NAVD88→MHHW→MLLW datum offsets |

**Example request:**
```json
{
  "station_id": "8724580",
  "scenario": "Intermediate",
  "target_year": 2070
}
```

**Response 200:**
```json
{
  "station_id": "8724580",
  "station_name": "Key West",
  "scenario": "Intermediate",
  "baseline_year": 2000,
  "target_year": 2070,
  "slr_m": 0.51,
  "slr_ft": 1.67,
  "confidence_low_m": 0.38,
  "confidence_high_m": 0.74,
  "datum_navd88_m": 0.0,
  "datum_mhhw_m": 0.281,
  "datum_mllw_m": -0.314,
  "source": "NOAA 2022 Sea Level Rise Technical Report (TR-083)",
  "units": "metric",
  "run_id": "slrw-20260320-142301-abc123",
  "elapsed_s": 0.14
}
```

**Response 422:** Validation error (missing/invalid fields)
**Response 500:** Internal error (NOAA API unreachable, etc.)

---

### `POST /inundation`

Run a bathtub inundation analysis using a DEM and SLR projection.

**Request body** (`application/json`):

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `station_id` | str | ✅ | — | NOAA CO-OPS station ID |
| `scenario` | str | ✅ | — | TR-083 scenario name |
| `target_year` | int | ✅ | — | Projection year |
| `dem_path` | str | ✅ | — | Absolute path to the input DEM raster (.tif) |
| `aoi_path` | str | ❌ | `null` | AOI shapefile (.shp) to clip analysis extent |
| `baseline_year` | int | ❌ | `2000` | Baseline datum epoch |
| `output_path` | str | ❌ | `null` | Output inundation raster path |

**Response 200:**
```json
{
  "station_id": "8724580",
  "scenario": "Intermediate",
  "target_year": 2070,
  "slr_m": 0.51,
  "inundated_area_sqkm": 12.45,
  "inundated_area_acres": 3077.3,
  "mean_depth_m": 0.21,
  "max_depth_m": 0.51,
  "dry_land_area_sqkm": 87.55,
  "percent_inundated": 12.46,
  "dem_path": "/data/dem/keys_1m.tif",
  "output_raster": "/output/inundation_2070_intermediate.tif",
  "run_id": "slrw-20260320-143201-def456",
  "elapsed_s": 4.72
}
```

---

### `GET /stations`

List available NOAA CO-OPS tide gauge stations.

**Query parameters:**
- `state` (str, optional): Filter by 2-letter state code (e.g. `FL`)
- `limit` (int, optional, default=50): Max results

**Response 200:**
```json
{
  "count": 12,
  "stations": [
    {"station_id": "8724580", "name": "Key West", "state": "FL",
     "lat": 24.5558, "lon": -81.8072, "slr_trend_mm_yr": 2.6},
    ...
  ]
}
```

---

### `GET /stations/{station_id}`

Get metadata for a single station.

**Response 200:**
```json
{
  "station_id": "8724580",
  "name": "Key West",
  "state": "FL",
  "lat": 24.5558,
  "lon": -81.8072,
  "datum_navd88_m": 0.0,
  "datum_mhhw_m": 0.281,
  "datum_mllw_m": -0.314,
  "slr_trend_mm_yr": 2.6,
  "slr_trend_start_yr": 1913,
  "slr_trend_end_yr": 2023
}
```

**Response 404:** Station not found

---

### `GET /scenarios`

List all available NOAA TR-083 SLR scenarios.

**Response 200:**
```json
{
  "scenarios": [
    {"name": "Low",              "description": "Low (17th percentile)", "2050_global_m": 0.10, "2100_global_m": 0.30},
    {"name": "Intermediate-Low", "description": "Intermediate-Low",     "2050_global_m": 0.18, "2100_global_m": 0.50},
    {"name": "Intermediate",     "description": "Intermediate (50th)",  "2050_global_m": 0.30, "2100_global_m": 1.00},
    {"name": "Intermediate-High","description": "Intermediate-High",    "2050_global_m": 0.43, "2100_global_m": 1.50},
    {"name": "High",             "description": "High (83rd percentile)","2050_global_m": 0.58, "2100_global_m": 2.00},
    {"name": "Extreme",          "description": "Extreme (99th)",       "2050_global_m": 0.82, "2100_global_m": 3.00}
  ]
}
```

---

### `GET /insights`

Query the SLR knowledge base.

**Query parameters:**
- `q` (str): Search query

**Response 200:**
```json
{
  "query": "NAVD88",
  "results": [
    {
      "topic": "navd88",
      "title": "NAVD88 Datum Reference",
      "body": "...",
      "tags": ["navd88", "datum", "slr"],
      "source": "NOAA VDatum"
    }
  ]
}
```

---

### `GET /health`

Liveness check for Docker / load balancer.

**Response 200:** `{"status": "ok", "uptime_s": 3721.4}`

---

## Configuration Classes

### `SLRInundationConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `station_id` | str | required | NOAA CO-OPS gauge ID |
| `scenario` | str | required | TR-083 scenario name |
| `target_year` | int | required | Projection horizon year |
| `baseline_year` | int | `2000` | Datum baseline epoch |
| `dem_path` | str | `None` | Input DEM path |
| `aoi_path` | str | `None` | AOI clip shapefile |
| `output_dir` | str | `"./output"` | Output directory |
| `include_tidal_datums` | bool | `False` | Datum conversion flag |

---

## Output Schema (`output_metadata`)

All `/slr` and `/inundation` responses include:

| Key | Type | Description |
|---|---|---|
| `run_id` | str | Unique run identifier |
| `elapsed_s` | float | Wall-clock execution time |
| `slr_m` | float | Sea-level rise in metres (NAVD88) |
| `slr_ft` | float | Sea-level rise in feet |
| `source` | str | Data source citation |
| `units` | str | `"metric"` |

---

## Error Codes

| HTTP | Meaning |
|---|---|
| 400 | Bad request (invalid station ID, unsupported scenario) |
| 404 | Station not found |
| 422 | Validation error (missing required field) |
| 500 | Internal server error (NOAA API failure, DEM I/O error) |
| 503 | Service temporarily unavailable |

---

## CLI Reference

```bash
# Run SLR projection
slr-wizard run --station 8724580 --scenario Intermediate --year 2070

# Run bathtub inundation
slr-wizard inundation --station 8724580 --scenario High --year 2100 \
    --dem /data/keys_dem.tif --output /output/

# List stations
slr-wizard stations --state FL

# Query knowledge base
slr-wizard insights --query "NAVD88"
```

---

*Reference: Sweet et al. (2022). 2022 Sea Level Rise Technical Report. NOAA.*
*https://oceanservice.noaa.gov/hazards/sealevelrise/sealevelrise-tech-report.html*
