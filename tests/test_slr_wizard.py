# -*- coding: utf-8 -*-
"""Tests for the CVG SLR Wizard package.
Requires storm-surge-wizard to be installed (slr_wizard.core delegates to it).
"""
from __future__ import annotations
import pytest
from slr_wizard.config import SLRWizardConfig, SLRSensitivityConfig
from slr_wizard.core import run_slr_analysis, project_slr, run_sensitivity, SLRResult


class TestSLRWizardConfig:
    def test_defaults(self):
        cfg = SLRWizardConfig()
        assert cfg.station_id == "8724580"
        assert cfg.scenario == "intermediate"
        assert cfg.target_year == 2100
        assert cfg.output_unit == "ft"
        assert cfg.baseline_water_levels_ft == {}

    def test_custom_values(self):
        cfg = SLRWizardConfig(station_id="8761724", scenario="high", target_year=2070,
                               baseline_water_levels_ft={"100yr": 8.5})
        assert cfg.station_id == "8761724"
        assert cfg.target_year == 2070
        assert cfg.baseline_water_levels_ft["100yr"] == 8.5


class TestProjectSlr:
    def test_key_west_intermediate_2100(self):
        slr_m, meta = project_slr("8724580", scenario="intermediate", target_year=2100)
        assert slr_m > 0.9
        assert meta["method"] == "noaa_tr083_table"

    def test_override_slr(self):
        slr_m, meta = project_slr("8724580", override_slr_m=0.42)
        assert slr_m == pytest.approx(0.42)
        assert meta["method"] == "override"

    def test_high_exceeds_intermediate(self):
        m_int, _ = project_slr("8724580", scenario="intermediate", target_year=2100)
        m_high, _ = project_slr("8724580", scenario="high", target_year=2100)
        assert m_high > m_int


class TestRunSlrAnalysis:
    def _cfg(self, **kwargs):
        defaults = dict(
            station_id="8724580",
            scenario="intermediate",
            target_year=2070,
            baseline_water_levels_ft={"10yr": 5.2, "100yr": 8.5, "500yr": 10.2},
        )
        defaults.update(kwargs)
        return SLRWizardConfig(**defaults)

    def test_returns_slr_result(self):
        result = run_slr_analysis(self._cfg())
        assert isinstance(result, SLRResult)

    def test_adjusted_levels_higher_than_baseline(self):
        result = run_slr_analysis(self._cfg())
        for label in result.baseline_water_levels:
            assert result.adjusted_water_levels[label] > result.baseline_water_levels[label]

    def test_delta_equals_slr_ft(self):
        result = run_slr_analysis(self._cfg())
        for label in result.baseline_water_levels:
            delta = result.adjusted_water_levels[label] - result.baseline_water_levels[label]
            assert delta == pytest.approx(result.slr_ft, abs=0.005)

    def test_sensitivity_has_six_scenarios(self):
        result = run_slr_analysis(self._cfg())
        assert len(result.sensitivity) == 6

    def test_no_baseline_dict_ok(self):
        cfg = SLRWizardConfig(station_id="8724580", scenario="low", target_year=2050)
        result = run_slr_analysis(cfg)
        assert result.slr_m > 0
        assert result.adjusted_water_levels == {}

    def test_override_slr_m(self):
        cfg = self._cfg(override_slr_m=0.30)
        result = run_slr_analysis(cfg)
        assert result.slr_m == pytest.approx(0.30)
        assert result.method == "override"

    def test_output_unit_metres(self):
        cfg = self._cfg(output_unit="m",
                        baseline_water_levels_ft={"100yr": 2.5},
                        baseline_unit="m")
        result = run_slr_analysis(cfg)
        expected_out = result.slr_m  # slr in metres
        delta = result.adjusted_water_levels["100yr"] - result.baseline_water_levels["100yr"]
        assert delta == pytest.approx(expected_out, abs=0.001)


class TestRunSensitivity:
    def test_returns_six_scenarios(self):
        result = run_sensitivity("8724580", target_year=2100)
        assert len(result) == 6

    def test_values_monotonically_increasing(self):
        from storm_surge_wizard.slr import SLR_SCENARIO_NAMES
        result = run_sensitivity("8724580", target_year=2100)
        vals = [result[sc]["slr_m"] for sc in SLR_SCENARIO_NAMES]
        for i in range(len(vals) - 1):
            assert vals[i] < vals[i + 1]


class TestWizardsBridge:
    def test_combine_surge_slr(self):
        from storm_surge_wizard.wizards import combine_surge_slr
        result = combine_surge_slr(
            {"100yr": 8.5, "500yr": 10.2},
            station_id="8724580",
            slr_scenario="intermediate",
            slr_year=2070,
        )
        assert "baseline" in result
        assert "adjusted" in result
        assert result["adjusted"]["100yr"] > result["baseline"]["100yr"]
        assert result["slr_m"] > 0

    def test_combine_surge_rainfall_additive(self):
        from storm_surge_wizard.wizards import combine_surge_rainfall
        r = combine_surge_rainfall(8.5, 0.3, slr=1.64, unit="ft")
        assert r["total_wse"] == pytest.approx(8.5 + 0.3 + 1.64, abs=0.001)

    def test_combine_surge_plus_slr_only(self):
        from storm_surge_wizard.wizards import combine_surge_rainfall
        r = combine_surge_rainfall(8.5, 0.3, slr=1.64, unit="ft",
                                   combination_method="surge_plus_slr")
        assert r["total_wse"] == pytest.approx(8.5 + 1.64, abs=0.001)

    def test_wizard_availability_storm_surge_always_true(self):
        from storm_surge_wizard.wizards import wizard_availability
        avail = wizard_availability()
        assert avail["storm_surge"] is True
