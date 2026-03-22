# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# CVG SLR Wizard — test_processing.py
# =============================================================================
"""Unit tests for slr_wizard.processing (bathtub inundation kernel)."""

import numpy as np
import pytest


def test_compute_bathtub_basic():
    """Simple flood: water surface at 2.0 ft; DEM ranges 0–4 ft."""
    from slr_wizard.processing import _compute_bathtub
    from slr_wizard.io import RasterData

    dem_data = np.array([[0.5, 1.0, 1.5, 2.5, 3.5]], dtype="float32")
    raster = RasterData(
        data=dem_data, transform=None, crs=None,
        nodata=-9999.0, width=5, height=1,
    )
    depth_grid, extent_grid = _compute_bathtub(
        raster, water_surface_ft=2.0, connected=False, connectivity="queen", min_depth=0.0
    )
    # Cells < 2.0: indices 0, 1, 2 should be wet
    wet = extent_grid.data[0]
    assert wet[0] == 1.0  # 0.5 ft below WSE
    assert wet[1] == 1.0  # 1.0 ft below WSE
    assert wet[2] == 1.0  # 1.5 ft below WSE
    assert wet[3] == 0.0  # 2.5 ft above WSE
    assert wet[4] == 0.0  # 3.5 ft above WSE


def test_compute_bathtub_depths():
    from slr_wizard.processing import _compute_bathtub
    from slr_wizard.io import RasterData

    dem_data = np.array([[0.0, 1.0, 2.0, 3.0]], dtype="float32")
    raster = RasterData(data=dem_data, transform=None, crs=None,
                        nodata=-9999.0, width=4, height=1)
    depth_grid, _ = _compute_bathtub(
        raster, water_surface_ft=2.5, connected=False, connectivity="queen", min_depth=0.0
    )
    depths = depth_grid.data[0]
    assert abs(depths[0] - 2.5) < 0.01   # 2.5 - 0.0
    assert abs(depths[1] - 1.5) < 0.01   # 2.5 - 1.0
    assert abs(depths[2] - 0.5) < 0.01   # 2.5 - 2.0
    assert depths[3] == depth_grid.nodata  # 3.0 > 2.5 → dry


def test_compute_bathtub_nodata_passthrough():
    from slr_wizard.processing import _compute_bathtub
    from slr_wizard.io import RasterData

    nodata = -9999.0
    dem_data = np.array([[nodata, 0.5, 1.5]], dtype="float32")
    raster = RasterData(data=dem_data, transform=None, crs=None,
                        nodata=nodata, width=3, height=1)
    depth_grid, extent_grid = _compute_bathtub(
        raster, water_surface_ft=2.0, connected=False, connectivity="queen", min_depth=0.0
    )
    assert depth_grid.data[0][0] == nodata     # nodata preserved
    assert extent_grid.data[0][1] == 1.0       # 0.5 < 2.0 → wet
    assert extent_grid.data[0][2] == 1.0       # 1.5 < 2.0 → wet


def test_min_depth_threshold():
    from slr_wizard.processing import _compute_bathtub
    from slr_wizard.io import RasterData

    dem_data = np.array([[0.0, 1.9, 1.5]], dtype="float32")  # small depths
    raster = RasterData(data=dem_data, transform=None, crs=None,
                        nodata=-9999.0, width=3, height=1)
    depth_grid, extent_grid = _compute_bathtub(
        raster, water_surface_ft=2.0, connected=False, connectivity="queen", min_depth=0.5
    )
    # depth[0] = 2.0 - 0.0 = 2.0 → keep
    # depth[1] = 2.0 - 1.9 = 0.1 → below 0.5 → nodata
    # depth[2] = 2.0 - 1.5 = 0.5 → exactly at threshold → keep
    assert depth_grid.data[0][0] != depth_grid.nodata
    assert depth_grid.data[0][1] == depth_grid.nodata
    assert depth_grid.data[0][2] != depth_grid.nodata


def test_ensure_feet_converts_meters():
    from slr_wizard.processing import _ensure_feet
    from slr_wizard.io import RasterData

    # Mean elevation ~5 m → should be converted
    dem_data = np.array([[4.0, 5.0, 6.0]], dtype="float32")
    raster = RasterData(data=dem_data, transform=None, crs=None,
                        nodata=-9999.0, width=3, height=1)
    result = _ensure_feet(raster)
    assert abs(result.data[0][0] - 4.0 * 3.28084) < 0.01


def test_ensure_feet_skips_already_feet():
    from slr_wizard.processing import _ensure_feet
    from slr_wizard.io import RasterData

    # Mean elevation well above 50 → already in feet
    dem_data = np.array([[55.0, 60.0, 65.0]], dtype="float32")
    raster = RasterData(data=dem_data, transform=None, crs=None,
                        nodata=-9999.0, width=3, height=1)
    result = _ensure_feet(raster)
    assert abs(result.data[0][0] - 55.0) < 0.01


def test_inundation_result_to_dict():
    from slr_wizard.processing import InundationResult
    r = InundationResult(
        run_id="test_001",
        scenario="intermediate",
        target_year=2050,
        slr_offset_ft=0.95,
        inundated_cells=100,
        total_cells=1000,
    )
    d = r.to_dict()
    assert d["run_id"] == "test_001"
    assert d["scenario"] == "intermediate"
    assert abs(d["inundated_pct"] - 10.0) < 0.01
