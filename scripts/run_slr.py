#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# CVG SLR Wizard — example run script
# Author: Alex Zelenski, GISP | azelenski@clearviewgeographic.com
# =============================================================================
"""
scripts/run_slr.py — Example script for running the SLR Wizard programmatically.

Edit the config below and run:
    python scripts/run_slr.py

Or use the CLI:
    slr-wizard run --config config.json
"""

import logging
import sys
from pathlib import Path

# Add project root to path if running from source
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ---------------------------------------------------------------------------
# Example 1: Quick SLR projection lookup (no DEM required)
# ---------------------------------------------------------------------------
def example_projection_lookup():
    from slr_wizard.noaa import get_all_scenarios_for_year

    print("\n" + "="*60)
    print("  NOAA TR-083 SLR Projections — Key West, FL (2070)")
    print("="*60)
    scenarios = get_all_scenarios_for_year(2070, station_id="8724580")
    print(f"  {'Scenario':22s}  {'ft':>8s}  {'m':>7s}")
    print("  " + "-"*44)
    for sc, ft in scenarios.items():
        m = ft / 3.28084
        print(f"  {sc:22s}  {ft:8.3f}  {m:7.3f}")
    print()


# ---------------------------------------------------------------------------
# Example 2: Run full inundation analysis (requires a real DEM)
# ---------------------------------------------------------------------------
def example_run_inundation(dem_path: str = "my_dem.tif"):
    from slr_wizard.config import (
        SLRWizardConfig, InputsConfig, SLRProjectionConfig,
        ProcessingConfig, OutputConfig, RunMetadata,
    )
    from slr_wizard.processing import run_inundation
    from slr_wizard.report import write_reports

    cfg = SLRWizardConfig(
        inputs=InputsConfig(
            dem_path=dem_path,
            noaa_station_id="8724580",   # Key West
        ),
        projection=SLRProjectionConfig(
            scenario="intermediate",
            target_year=2050,
            baseline_datum="NAVD88",
            apply_tidal_datum_shift=True,
        ),
        processing=ProcessingConfig(
            connected_inundation=True,
            connectivity_method="queen",
            min_depth_ft=0.1,
        ),
        output=OutputConfig(
            output_dir="output",
            output_prefix="slr_kw",
            write_depth_grid=True,
            write_extent_vector=True,
            generate_pdf_report=True,
            generate_json_report=True,
        ),
        metadata=RunMetadata(
            project_name="Key West 2050 SLR Study",
            analyst="Alex Zelenski",
        ),
    )

    result = run_inundation(cfg, resume=True)
    paths = write_reports(result, cfg, cfg.output.output_dir)

    print(f"\n  Run complete: {result.run_id}")
    print(f"  SLR offset : {result.slr_offset_ft:.3f} ft")
    print(f"  Inundated  : {result.inundated_pct:.1f}%  ({result.inundated_cells:,} cells)")
    print(f"  Max depth  : {result.max_depth_ft:.2f} ft")
    for fmt, path in paths.items():
        print(f"  [{fmt.upper()}] {path}")


# ---------------------------------------------------------------------------
# Example 3: Batch run all scenarios × 2050 and 2100
# ---------------------------------------------------------------------------
def example_batch_run(dem_path: str = "my_dem.tif"):
    from slr_wizard.config import (
        SLRWizardConfig, InputsConfig, SLRProjectionConfig,
        ProcessingConfig, OutputConfig,
    )
    from slr_wizard.processing import run_batch

    cfg = SLRWizardConfig(
        inputs=InputsConfig(dem_path=dem_path, noaa_station_id="8724580"),
        processing=ProcessingConfig(
            run_all_scenarios=True,
            batch_years=[2050, 2100],
            connected_inundation=True,
        ),
        output=OutputConfig(output_dir="output_batch"),
    )

    results = run_batch(cfg)
    print(f"\n  Batch: {len(results)} runs completed")
    for r in results:
        print(f"  {r.scenario:22s} {r.target_year}  → {r.inundated_pct:.1f}%  max={r.max_depth_ft:.2f} ft")


# ---------------------------------------------------------------------------
# Example 4: Run sensitivity analysis
# ---------------------------------------------------------------------------
def example_sensitivity():
    from slr_wizard.core import run_sensitivity

    sens = run_sensitivity("8724580", target_year=2070)
    print("\n  Sensitivity Table — Key West, 2070")
    print(f"  {'Scenario':22s}  {'m':>7s}  {'ft':>8s}")
    print("  " + "-"*44)
    for sc, vals in sens.items():
        print(f"  {sc:22s}  {vals['slr_m']:7.3f}  {vals['slr_ft']:8.3f}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    example_projection_lookup()
    example_sensitivity()
    # Uncomment to run with a real DEM:
    # example_run_inundation("path/to/your/dem.tif")
    # example_batch_run("path/to/your/dem.tif")
