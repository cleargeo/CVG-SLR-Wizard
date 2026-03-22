# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# CVG SLR Wizard — test_noaa.py
# =============================================================================
"""Unit tests for slr_wizard.noaa (SLR projection table)."""

import pytest
from slr_wizard.noaa import (
    get_slr_projection,
    get_all_scenarios_for_year,
    list_supported_stations,
    _SLR_TABLE,
    _DEFAULT_SLR_FT,
)
from slr_wizard.config import VALID_SCENARIOS


def test_intermediate_key_west_2050():
    """Known value: Key West, intermediate, 2050."""
    val = get_slr_projection("intermediate", 2050, station_id="8724580")
    assert abs(val - 0.95) < 0.02


def test_intermediate_2100_national_avg():
    val = get_slr_projection("intermediate", 2100, station_id=None)
    assert 3.0 < val < 5.0  # nationally ~3.8 ft


def test_all_scenarios_for_year_count():
    results = get_all_scenarios_for_year(2070, station_id="8724580")
    assert len(results) == len(VALID_SCENARIOS)
    for sc, ft in results.items():
        assert ft >= 0.0, f"Negative SLR for {sc}"


def test_scenarios_ordered_low_to_extreme():
    """Higher scenarios must produce larger SLR values."""
    rslr = get_all_scenarios_for_year(2100, station_id="8724580")
    vals = [rslr[sc] for sc in VALID_SCENARIOS]
    for i in range(len(vals) - 1):
        assert vals[i] <= vals[i + 1], (
            f"Scenario order violated: {VALID_SCENARIOS[i]} >= {VALID_SCENARIOS[i+1]}"
        )


def test_interpolation_between_decades():
    """Requesting year 2055 should interpolate between 2050 and 2060."""
    v2050 = get_slr_projection("intermediate", 2050, station_id="8724580")
    v2060 = get_slr_projection("intermediate", 2060, station_id="8724580")
    v2055 = get_slr_projection("intermediate", 2055, station_id="8724580")
    assert v2050 <= v2055 <= v2060


def test_pre_table_year_clamps_to_first():
    val = get_slr_projection("intermediate", 1990, station_id="8724580")
    assert val == get_slr_projection("intermediate", 2030, station_id="8724580")


def test_post_table_year_clamps_to_last():
    val = get_slr_projection("intermediate", 2150, station_id="8724580")
    assert val == get_slr_projection("intermediate", 2100, station_id="8724580")


def test_unknown_scenario_raises():
    with pytest.raises(ValueError):
        get_slr_projection("catastrophic", 2050)


def test_unknown_station_uses_default():
    val = get_slr_projection("intermediate", 2050, station_id="9999999")
    default_val = _DEFAULT_SLR_FT["intermediate"][2050]
    assert abs(val - default_val) < 0.01


def test_list_supported_stations():
    stations = list_supported_stations()
    assert len(stations) >= 6
    ids = [s.station_id for s in stations]
    assert "8724580" in ids  # Key West


def test_station_metadata_valid():
    stations = list_supported_stations()
    for s in stations:
        assert s.station_id
        assert s.name
        assert -180 <= s.lon <= 180
        assert -90 <= s.lat <= 90
