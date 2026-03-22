# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# Proprietary Software -- Internal Use Only
# =============================================================================
"""CVG SLR Wizard — Sea Level Rise analysis, scenario projection, and storm surge adjustment.

© Clearview Geographic, LLC — All Rights Reserved | Est. 2018
Proprietary Software — Internal Use Only

This package implements a **fully self-contained** SLR projection engine based on
NOAA Technical Report NOS CO-OPS 083 (Sweet et al. 2022) — *zero dependency on
storm_surge_wizard*. It covers 14 NOAA CO-OPS tide gauge stations with 6 RSLR
scenarios (Low → Extreme) and supports arbitrary planning horizons 2020–2100 via
linear interpolation. Storm surge Water Surface Elevations (WSE) can be elevated
by the RSLR offset to produce combined compound-hazard WSEs.

Two analysis modes are available:

**Mode 1 — Projection-only** (no DEM required)::

    from slr_wizard import run_slr_analysis, SLRWizardConfig

    cfg = SLRWizardConfig(
        station_id="8724580",      # Key West, FL
        scenario="intermediate",
        target_year=2070,
        baseline_water_levels_ft={"10yr": 5.2, "100yr": 8.5, "500yr": 10.2},
    )
    result = run_slr_analysis(cfg)
    print(result.adjusted_water_levels_ft)

**Mode 2 — Bathtub inundation grid** (requires DEM GeoTIFF)::

    from slr_wizard import (
        run_inundation, SLRInundationConfig,
        InputsConfig, SLRProjectionConfig, OutputConfig, RunMetadata,
    )

    cfg = SLRInundationConfig(
        inputs=InputsConfig(dem_path="/data/dem.tif", noaa_station_id="8724580"),
        projection=SLRProjectionConfig(scenario="intermediate", target_year=2070),
        output=OutputConfig(output_dir="/data/slr_output"),
        metadata=RunMetadata(project_name="Monroe County SLR 2070"),
    )
    result = run_inundation(cfg, resume=False)
    print(result.depth_grid_path, result.max_depth_ft)
"""
from __future__ import annotations

# ── Simple projection-only API ────────────────────────────────────────────────
from slr_wizard.config import SLRWizardConfig, SLRSensitivityConfig
from slr_wizard.core import run_slr_analysis, project_slr, SLRResult

# ── Full inundation engine API ────────────────────────────────────────────────
from slr_wizard.config import (
    SLRInundationConfig,
    InputsConfig,
    SLRProjectionConfig,
    ProcessingConfig,
    OutputConfig,
    RunMetadata,
    validate_config,
    VALID_SCENARIOS,
)
from slr_wizard.processing import run_inundation, InundationResult

__version__ = "1.1.0"

__all__ = [
    # ── Projection-only (no DEM) ──────────────────────────────────────────
    "SLRWizardConfig",
    "SLRSensitivityConfig",
    "run_slr_analysis",
    "project_slr",
    "SLRResult",
    # ── Full bathtub inundation (DEM required) ───────────────────────────
    "SLRInundationConfig",
    "InputsConfig",
    "SLRProjectionConfig",
    "ProcessingConfig",
    "OutputConfig",
    "RunMetadata",
    "validate_config",
    "run_inundation",
    "InundationResult",
    # ── Constants ────────────────────────────────────────────────────────
    "VALID_SCENARIOS",
]
