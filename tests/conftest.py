# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# CVG SLR Wizard — pytest conftest
# =============================================================================
"""Shared pytest fixtures for the SLR Wizard test suite."""

import numpy as np
import pytest


@pytest.fixture
def sample_dem_array():
    """5×5 DEM array (NAVD88 elevations in feet, coastal area)."""
    return np.array([
        [-0.5, 0.2, 0.8, 1.5, 2.2],
        [-0.3, 0.5, 1.1, 1.8, 2.5],
        [ 0.1, 0.9, 1.5, 2.2, 3.0],
        [ 0.8, 1.4, 2.0, 2.7, 3.5],
        [ 1.5, 2.0, 2.7, 3.3, 4.0],
    ], dtype="float32")


@pytest.fixture
def nodata_value():
    return -9999.0


@pytest.fixture
def mock_raster_data(sample_dem_array, nodata_value):
    """Minimal RasterData-like object for testing."""
    class _FakeTransform:
        a = 1.0
        e = -1.0

    class _FakeCRS:
        pass

    from slr_wizard.io import RasterData
    return RasterData(
        data=sample_dem_array,
        transform=_FakeTransform(),
        crs=_FakeCRS(),
        nodata=nodata_value,
        width=5,
        height=5,
    )


@pytest.fixture
def basic_config():
    """Minimal SLRInundationConfig with safe defaults (no real DEM path).

    NOTE: Use SLRInundationConfig (nested) for the inundation engine, NOT the
    flat SLRWizardConfig which only holds projection-only (no DEM) parameters.
    """
    from slr_wizard.config import (
        SLRInundationConfig, InputsConfig, SLRProjectionConfig,
        ProcessingConfig, OutputConfig,
    )
    cfg = SLRInundationConfig(
        inputs=InputsConfig(dem_path="fake.tif", noaa_station_id="8724580"),
        projection=SLRProjectionConfig(scenario="intermediate", target_year=2050),
        processing=ProcessingConfig(connected_inundation=False),
        output=OutputConfig(output_dir="output_test"),
    )
    return cfg


@pytest.fixture
def flat_config():
    """Minimal SLRWizardConfig (flat, projection-only, no DEM required)."""
    from slr_wizard.config import SLRWizardConfig
    return SLRWizardConfig(
        station_id="8724580",
        scenario="intermediate",
        target_year=2050,
        baseline_water_levels_ft={"10yr": 5.2, "100yr": 8.5},
    )
