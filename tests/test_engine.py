# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# Proprietary Software -- Internal Use Only
# Protected under US and International copyright, trade secret,
# trademark, cybersecurity, and intellectual property law.
# This Product is developed under CVG's Agentic Development Framework (ADF).
# Unauthorized use, replication, or modification is strictly prohibited.
# -----------------------------------------------------------------------------
# Author      : Alex Zelenski, GISP
# Organization: Clearview Geographic, LLC
# Contact     : azelenski@clearviewgeographic.com  |  386-957-2314
#               contact@clearviewgeographic.com (org)
# GitHub      : azelenski_cvg | clearview-geographic (Enterprise) | cleargeo (Public)
# Website     : https://www.clearviewgeographic.com
# License     : Proprietary -- CVG-ADF | See Software-Disclaimer-License-Header.md
# =============================================================================
"""Direct unit tests for slr_wizard.engine — NOAA TR-083 standalone SLR engine.

Tests cover:
- get_slr_projection() with keyword-only args (target_year=, scenario=)
- resolve_slr_scenario() alias resolution
- get_slr_sensitivity() all-scenario sweep
- resolve_slr_offset() via SLRConfig
- Linear interpolation between decadal anchors
- Boundary clamping (year < 2020, year > 2100)
- Fallback to Key West proxy for unknown station
- list_slr_scenarios() and list_slr_stations() shape/contents
- SLRConfig dataclass defaults
- Storm surge + SLR combination pattern (WSE + RSLR offset)
- Zero-dependency assertion: no storm_surge_wizard import in engine module
"""
from __future__ import annotations

import importlib
import inspect
import sys
import types

import pytest

from slr_wizard.engine import (
    SLR_PROJECTIONS,
    SLR_SCENARIO_NAMES,
    SLR_SCENARIO_ALIASES,
    SLR_STATION_METADATA,
    SLRConfig,
    get_slr_projection,
    get_slr_sensitivity,
    list_slr_scenarios,
    list_slr_stations,
    resolve_slr_offset,
    resolve_slr_scenario,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KEY_WEST = "8724580"
GRAND_ISLE = "8761724"
CHARLESTON = "8665530"


# ---------------------------------------------------------------------------
# Zero-dependency check
# ---------------------------------------------------------------------------

class TestZeroDependency:
    """engine.py must have NO runtime dependency on storm_surge_wizard."""

    def test_engine_has_no_ssw_import_statement(self):
        """engine.py must contain no 'import storm_surge_wizard' or 'from storm_surge_wizard' line."""
        import slr_wizard.engine as eng_mod
        src = inspect.getsource(eng_mod)
        import re
        # Match actual import statements only, not doc string mentions
        ssw_imports = re.findall(
            r'^\s*(?:import|from)\s+storm_surge_wizard',
            src,
            re.MULTILINE,
        )
        assert ssw_imports == [], (
            f"engine.py has actual storm_surge_wizard import(s): {ssw_imports}. "
            "It must be fully standalone."
        )

    def test_ssw_not_in_sys_modules_after_engine_import(self):
        """storm_surge_wizard should NOT be in sys.modules after a fresh engine import."""
        import slr_wizard.engine  # noqa: F401
        ssw_keys = [k for k in sys.modules if k.startswith("storm_surge_wizard")]
        assert ssw_keys == [], (
            f"storm_surge_wizard was imported as a side-effect: {ssw_keys}"
        )


# ---------------------------------------------------------------------------
# Scenario alias resolution
# ---------------------------------------------------------------------------

class TestResolveSlrScenario:

    @pytest.mark.parametrize("alias,expected", [
        ("l",                "low"),
        ("low",              "low"),
        ("il",               "intermediate_low"),
        ("int_low",          "intermediate_low"),
        ("intlow",           "intermediate_low"),
        ("intermediate_low", "intermediate_low"),
        ("i",                "intermediate"),
        ("int",              "intermediate"),
        ("intermediate",     "intermediate"),
        ("ih",               "intermediate_high"),
        ("int_high",         "intermediate_high"),
        ("inthigh",          "intermediate_high"),
        ("intermediate_high","intermediate_high"),
        ("h",                "high"),
        ("high",             "high"),
        ("e",                "extreme"),
        ("extreme",          "extreme"),
    ])
    def test_alias_resolves_correctly(self, alias, expected):
        assert resolve_slr_scenario(alias) == expected

    def test_case_insensitive(self):
        assert resolve_slr_scenario("INTERMEDIATE") == "intermediate"
        assert resolve_slr_scenario("IH") == "intermediate_high"
        assert resolve_slr_scenario("High") == "high"

    def test_unknown_alias_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown SLR scenario"):
            resolve_slr_scenario("rcp85")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            resolve_slr_scenario("")


# ---------------------------------------------------------------------------
# get_slr_projection — keyword-only API
# ---------------------------------------------------------------------------

class TestGetSlrProjection:
    """All calls MUST use keyword-only args: target_year=, scenario=."""

    def test_key_west_intermediate_2070_exact(self):
        """NOAA TR-083 benchmark: Key West intermediate 2070 = 0.5600 m."""
        m = get_slr_projection(KEY_WEST, target_year=2070, scenario="intermediate")
        assert m == pytest.approx(0.5600, abs=1e-4)

    def test_key_west_extreme_2100_exact(self):
        """NOAA TR-083 benchmark: Key West extreme 2100 = 3.22 m."""
        m = get_slr_projection(KEY_WEST, target_year=2100, scenario="extreme")
        assert m == pytest.approx(3.22, abs=1e-4)

    def test_grand_isle_intermediate_2100(self):
        """Grand Isle (high subsidence) intermediate 2100 = 2.44 m."""
        m = get_slr_projection(GRAND_ISLE, target_year=2100, scenario="intermediate")
        assert m == pytest.approx(2.44, abs=1e-4)

    def test_charleston_high_2100(self):
        """Charleston high 2100 = 2.48 m."""
        m = get_slr_projection(CHARLESTON, target_year=2100, scenario="high")
        assert m == pytest.approx(2.48, abs=1e-4)

    def test_linear_interpolation_midpoint(self):
        """Key West intermediate 2065 should be midpoint between 2060 and 2070 values."""
        m_2060 = get_slr_projection(KEY_WEST, target_year=2060, scenario="intermediate")
        m_2070 = get_slr_projection(KEY_WEST, target_year=2070, scenario="intermediate")
        m_2065 = get_slr_projection(KEY_WEST, target_year=2065, scenario="intermediate")
        expected = (m_2060 + m_2070) / 2
        assert m_2065 == pytest.approx(expected, abs=1e-5)

    def test_below_range_clamps_to_2020(self):
        """Year < 2020 should clamp to 2020 anchor value."""
        m_2019 = get_slr_projection(KEY_WEST, target_year=2019, scenario="intermediate")
        m_2020 = get_slr_projection(KEY_WEST, target_year=2020, scenario="intermediate")
        assert m_2019 == pytest.approx(m_2020, abs=1e-9)

    def test_above_range_clamps_to_2100(self):
        """Year > 2100 should clamp to 2100 anchor value."""
        m_2101 = get_slr_projection(KEY_WEST, target_year=2101, scenario="intermediate")
        m_2100 = get_slr_projection(KEY_WEST, target_year=2100, scenario="intermediate")
        assert m_2101 == pytest.approx(m_2100, abs=1e-9)

    def test_alias_ih_same_as_intermediate_high(self):
        """Alias 'ih' must match canonical 'intermediate_high'."""
        m_alias = get_slr_projection(KEY_WEST, target_year=2070, scenario="ih")
        m_canon = get_slr_projection(KEY_WEST, target_year=2070, scenario="intermediate_high")
        assert m_alias == pytest.approx(m_canon, abs=1e-9)

    def test_alias_il_same_as_intermediate_low(self):
        m_alias = get_slr_projection(KEY_WEST, target_year=2050, scenario="il")
        m_canon = get_slr_projection(KEY_WEST, target_year=2050, scenario="intermediate_low")
        assert m_alias == pytest.approx(m_canon, abs=1e-9)

    def test_unknown_station_falls_back_to_key_west(self, caplog):
        """Unknown station should warn and fall back to Key West proxy."""
        import logging
        with caplog.at_level(logging.WARNING, logger="slr_wizard.engine"):
            m = get_slr_projection("9999999", target_year=2070, scenario="intermediate")
        m_kw = get_slr_projection(KEY_WEST, target_year=2070, scenario="intermediate")
        assert m == pytest.approx(m_kw, abs=1e-9)
        assert "9999999" in caplog.text or "Key West" in caplog.text

    def test_returns_float(self):
        result = get_slr_projection(KEY_WEST, target_year=2070, scenario="low")
        assert isinstance(result, float)

    def test_all_14_stations_return_positive(self):
        """Every station should return a positive RSLR value for a mid-horizon year."""
        for station_id in SLR_PROJECTIONS:
            m = get_slr_projection(station_id, target_year=2070, scenario="intermediate")
            assert m > 0, f"Station {station_id}: expected positive RSLR, got {m}"

    def test_all_6_scenarios_ordered_by_magnitude(self):
        """For any station/year, scenario magnitudes must be monotonically ordered."""
        order = ["low", "intermediate_low", "intermediate", "intermediate_high", "high", "extreme"]
        values = [get_slr_projection(KEY_WEST, target_year=2070, scenario=s) for s in order]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1], (
                f"Expected {order[i]} < {order[i+1]}, "
                f"got {values[i]:.4f} vs {values[i+1]:.4f}"
            )

    def test_positional_arg_for_station_id_only(self):
        """station_id is positional; target_year and scenario are keyword-only (force)."""
        # This should work fine (station_id as first positional)
        m = get_slr_projection(KEY_WEST, target_year=2050, scenario="intermediate")
        assert m > 0

    def test_keyword_only_enforcement(self):
        """target_year and scenario cannot be passed as positional — they follow *."""
        with pytest.raises(TypeError):
            get_slr_projection(KEY_WEST, 2070, "intermediate")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# get_slr_sensitivity
# ---------------------------------------------------------------------------

class TestGetSlrSensitivity:

    def test_returns_all_six_scenarios(self):
        sens = get_slr_sensitivity(KEY_WEST, target_year=2070)
        assert set(sens.keys()) == set(SLR_SCENARIO_NAMES)

    def test_values_match_individual_lookups(self):
        sens = get_slr_sensitivity(KEY_WEST, target_year=2070)
        for scenario in SLR_SCENARIO_NAMES:
            expected = get_slr_projection(KEY_WEST, target_year=2070, scenario=scenario)
            assert sens[scenario] == pytest.approx(expected, abs=1e-9)

    def test_returns_dict_of_floats(self):
        sens = get_slr_sensitivity(KEY_WEST, target_year=2070)
        for k, v in sens.items():
            assert isinstance(k, str)
            assert isinstance(v, float)


# ---------------------------------------------------------------------------
# Storm surge + SLR combination (core use case)
# ---------------------------------------------------------------------------

class TestStormSurgePlusSLR:

    @pytest.mark.parametrize("baseline_ft,scenario,year,expected_min,expected_max", [
        (10.0, "intermediate", 2070, 11.5, 12.5),    # ~10 + 1.84 ft = 11.84
        (10.0, "extreme",     2100, 10.0 + 3.21*3.28084 - 0.1,
                                    10.0 + 3.21*3.28084 + 0.3),  # extreme 2100
        (5.0,  "low",         2050, 5.3, 5.8),       # low SLR is minimal
    ])
    def test_combined_wse_range(self, baseline_ft, scenario, year, expected_min, expected_max):
        """Combined WSE = baseline surge + RSLR offset, in feet."""
        slr_m = get_slr_projection(KEY_WEST, target_year=year, scenario=scenario)
        slr_ft = slr_m * 3.28084
        combined = baseline_ft + slr_ft
        assert expected_min <= combined <= expected_max, (
            f"Combined WSE {combined:.3f} ft out of expected range "
            f"[{expected_min}, {expected_max}] for scenario={scenario}, year={year}"
        )

    def test_slr_always_increases_wse(self):
        """RSLR offset is always ≥ 0 so combined WSE ≥ baseline for any valid scenario/year."""
        baseline = 8.0
        for scenario in SLR_SCENARIO_NAMES:
            for year in [2030, 2050, 2070, 2100]:
                slr_m = get_slr_projection(KEY_WEST, target_year=year, scenario=scenario)
                combined = baseline + slr_m * 3.28084
                assert combined >= baseline


# ---------------------------------------------------------------------------
# resolve_slr_offset (SLRConfig → metres)
# ---------------------------------------------------------------------------

class TestResolveSlrOffset:

    def test_disabled_returns_zero(self):
        cfg = SLRConfig(enabled=False, station_id=KEY_WEST, scenario="intermediate", target_year=2070)
        slr_m, meta = resolve_slr_offset(cfg)
        assert slr_m == 0.0
        assert meta["slr_m"] == 0.0

    def test_enabled_returns_positive(self):
        cfg = SLRConfig(enabled=True, station_id=KEY_WEST, scenario="intermediate", target_year=2070)
        slr_m, meta = resolve_slr_offset(cfg)
        assert slr_m == pytest.approx(0.5600, abs=1e-4)
        assert meta["method"] == "noaa_tr083_table"

    def test_override_bypasses_table(self):
        cfg = SLRConfig(enabled=True, station_id=KEY_WEST, override_slr_m=0.999)
        slr_m, meta = resolve_slr_offset(cfg)
        assert slr_m == pytest.approx(0.999, abs=1e-9)
        assert meta["method"] == "override"

    def test_meta_includes_ft_conversion(self):
        cfg = SLRConfig(enabled=True, station_id=KEY_WEST, scenario="intermediate", target_year=2070)
        slr_m, meta = resolve_slr_offset(cfg)
        assert meta["slr_ft"] == pytest.approx(slr_m * 3.28084, abs=1e-4)

    def test_meta_includes_noaa_reference(self):
        cfg = SLRConfig(enabled=True, station_id=KEY_WEST, scenario="low", target_year=2050)
        _, meta = resolve_slr_offset(cfg)
        assert "Sweet et al." in meta.get("noaa_tr083_reference", "")


# ---------------------------------------------------------------------------
# SLRConfig dataclass
# ---------------------------------------------------------------------------

class TestSLRConfig:

    def test_defaults(self):
        cfg = SLRConfig()
        assert cfg.enabled is False
        assert cfg.scenario == "intermediate"
        assert cfg.target_year == 2100
        assert cfg.station_id == ""
        assert cfg.override_slr_m is None
        assert cfg.apply_to_all_scenarios is True

    def test_custom_values(self):
        cfg = SLRConfig(
            enabled=True,
            scenario="high",
            target_year=2070,
            station_id=KEY_WEST,
            notes="Test run",
        )
        assert cfg.enabled is True
        assert cfg.scenario == "high"
        assert cfg.target_year == 2070
        assert cfg.station_id == KEY_WEST
        assert cfg.notes == "Test run"


# ---------------------------------------------------------------------------
# list_slr_scenarios and list_slr_stations
# ---------------------------------------------------------------------------

class TestListFunctions:

    def test_list_scenarios_returns_six(self):
        scenarios = list_slr_scenarios()
        assert len(scenarios) == 6

    def test_list_scenarios_keys(self):
        for sc in list_slr_scenarios():
            assert "name" in sc
            assert "global_mean_2100_m" in sc
            assert "global_mean_2100_ft" in sc
            assert "description" in sc

    def test_list_scenarios_names_match_canonical(self):
        names = [s["name"] for s in list_slr_scenarios()]
        assert names == list(SLR_SCENARIO_NAMES)

    def test_list_stations_returns_14(self):
        stations = list_slr_stations()
        assert len(stations) == 14

    def test_list_stations_includes_key_west(self):
        ids = [s["station_id"] for s in list_slr_stations()]
        assert KEY_WEST in ids

    def test_list_stations_keys(self):
        for st in list_slr_stations():
            assert "station_id" in st
            assert "name" in st
            assert "region" in st

    def test_scenario_global_mean_ordered(self):
        """Global-mean 2100 values should be monotonically increasing across scenarios."""
        gm = [s["global_mean_2100_m"] for s in list_slr_scenarios()]
        for i in range(len(gm) - 1):
            assert gm[i] < gm[i + 1]

    def test_ft_conversion_consistent(self):
        """global_mean_2100_ft should equal global_mean_2100_m × 3.28084."""
        for sc in list_slr_scenarios():
            expected_ft = round(sc["global_mean_2100_m"] * 3.28084, 3)
            assert sc["global_mean_2100_ft"] == pytest.approx(expected_ft, abs=0.001)
