<!--
  © Clearview Geographic LLC -- All Rights Reserved | Est. 2018
  Proprietary Software -- Internal Use Only
  Author      : Alex Zelenski, GISP
  Organization: Clearview Geographic, LLC
  Contact     : azelenski@clearviewgeographic.com | 386-957-2314
  GitHub      : azelenski_cvg | clearview-geographic (Enterprise) | cleargeo (Public)
  Website     : https://www.clearviewgeographic.com
  License     : Proprietary -- CVG-ADF
  Version     : v1.1.1 | ChangeID: 20260321-AZ-v1.1.1
-->

# CVG SLR Wizard

> **© Clearview Geographic LLC** — Proprietary | Author: Alex Zelenski, GISP
> `azelenski@clearviewgeographic.com` | 386-957-2314 | [clearviewgeographic.com](https://www.clearviewgeographic.com)
> **Version:** v1.1.1 | **License:** Proprietary – CVG-ADF | **ChangeID:** `20260321-AZ-v1.1.1`

A Python toolkit for building **Sea Level Rise (SLR) inundation grids** (GeoTIFF) by combining:
- A Digital Elevation Model (DEM)
- NOAA TR-083 relative sea level rise projections (Sweet et al. 2022)
- Tidal datum offsets from NOAA VDatum

---

## Features

| Feature | Details |
|---|---|
| **NOAA TR-083 Scenarios** | All 6 RSLR scenarios: Low → Extreme, 2030–2100 |
| **Station-Specific RSLR** | 6 CONUS CO-OPS stations with embedded tables; national avg fallback |
| **VDatum Integration** | Local JAR (preferred) + REST API fallback for datum transforms |
| **Bathtub Inundation** | Queen/rook connectivity filter; minimum depth threshold |
| **Batch Mode** | All scenarios × all years in one command |
| **JSON + PDF Reports** | Structured reports with full provenance |
| **FastAPI Web UI** | REST API on port 8010 + Jinja2 templates |
| **Checkpoint/Resume** | Interrupt a long run and pick up where it stopped |
| **Knowledge Base** | 7 built-in guidance topics (NOAA, FEMA, adaptation strategies) |

---

## Quick Start

### CLI

```bash
# Generate a default config file
slr-wizard new-config --output my_slr.json

# Edit my_slr.json — set dem_path, noaa_station_id, scenario, target_year, etc.

# Run inundation analysis
slr-wizard run --config my_slr.json

# Run all 6 scenarios × 2050 + 2100
slr-wizard batch --config my_slr.json

# Quick projection lookup (no DEM required)
slr-wizard project --station 8724580 --year 2070

# Start web server
slr-wizard web --port 8010
```

### Python API

```python
from slr_wizard import SLRWizardConfig, InputsConfig, SLRProjectionConfig, run_slr_analysis

cfg = SLRWizardConfig(
    inputs=InputsConfig(dem_path="my_dem.tif", noaa_station_id="8724580"),
    projection=SLRProjectionConfig(scenario="intermediate", target_year=2050),
)
result = run_slr_analysis(cfg)
print(f"SLR: {result.slr_ft:.2f} ft  |  {result.inundated_pct:.1f}% inundated")
```

### Quick SLR Projection

```python
from slr_wizard.noaa import get_all_scenarios_for_year

projections = get_all_scenarios_for_year(2070, station_id="8724580")
for scenario, ft in projections.items():
    print(f"{scenario:22s}: {ft:.2f} ft")
```

---

## NOAA SLR Scenarios (Sweet et al. 2022 / TR-083)

| Scenario | 2050 (ft) | 2100 (ft) | Use Case |
|---|---|---|---|
| Low | 0.5 | 1.6 | Lower bound; thermostatic only |
| Intermediate-Low | 0.7 | 2.5 | Moderate acceleration |
| **Intermediate** | **1.0** | **3.8** | **NOAA/FEMA recommended baseline** |
| Intermediate-High | 1.3 | 5.5 | Risk-informed upper bound |
| High | 1.6 | 7.3 | Significant WAIS contribution |
| Extreme | 2.0 | 12.1 | IPCC high-end; precautionary only |

Values shown are national averages. Station-specific RSLR accounts for local vertical land motion.

---

## Supported NOAA CO-OPS Stations

| Station ID | Name | State |
|---|---|---|
| 8724580 | Key West | FL |
| 8720218 | Mayport | FL |
| 8665530 | Charleston | SC |
| 8638610 | Norfolk | VA |
| 8771341 | Galveston Pier 21 | TX |
| 8761724 | Grand Isle | LA |

Use `slr-wizard stations` to list all stations.

---

## Configuration File (JSON)

```json
{
  "inputs": {
    "dem_path": "path/to/dem.tif",
    "aoi_path": "",
    "noaa_station_id": "8724580"
  },
  "projection": {
    "scenario": "intermediate",
    "target_year": 2050,
    "baseline_datum": "NAVD88",
    "apply_tidal_datum_shift": true
  },
  "processing": {
    "connected_inundation": true,
    "min_depth_ft": 0.1,
    "run_all_scenarios": false,
    "batch_years": [2050, 2100]
  },
  "output": {
    "output_dir": "output",
    "output_prefix": "slr_inundation",
    "write_depth_grid": true,
    "write_extent_vector": true,
    "generate_pdf_report": true
  },
  "metadata": {
    "project_name": "My SLR Study",
    "analyst": "Alex Zelenski"
  }
}
```

---

## Installation

```bash
# Development install
pip install -e ".[web]"

# Or Docker
docker compose up
```

Dependencies: `rasterio`, `numpy`, `fiona`, `fastapi`, `uvicorn`, `jinja2`, `psutil`, `reportlab`

---

## Docker

```bash
# Build and start
docker compose up --build

# API available at http://localhost:8010
# Swagger docs at http://localhost:8010/docs
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check / version |
| GET | `/api/stations` | List supported stations |
| GET | `/api/project?year=2070&scenario=intermediate` | SLR projection lookup |
| POST | `/api/run` | Run inundation analysis |
| GET | `/api/insights?q=datum` | Search knowledge base |

---

## References

> Sweet, W.V., B.D. Hamlington, R.E. Kopp, C.P. Weaver et al. (2022). *Global and Regional Sea Level Rise Scenarios for the United States.* NOAA Technical Report NOS CO-OPS 083. NOAA/NOS Center for Operational Oceanographic Products and Services. Silver Spring, MD.
> https://oceanservice.noaa.gov/hazards/sealevelrise/sealevelrise-tech-report.html

---

*© Clearview Geographic LLC — Proprietary Software — All Rights Reserved*
*Unauthorized use, replication, or modification is strictly prohibited.*
