# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# CVG SLR Wizard — test_config.py
# =============================================================================
"""Unit tests for slr_wizard.config."""

import json
import pytest
from pathlib import Path


def test_default_config_is_valid_structure():
    from slr_wizard.config import SLRInundationConfig
    cfg = SLRInundationConfig()
    assert cfg.projection.scenario == "intermediate"
    assert cfg.projection.target_year == 2050
    assert cfg.projection.baseline_datum == "NAVD88"
    assert cfg.processing.connected_inundation is True
    assert cfg.output.write_depth_grid is True


def test_valid_scenarios_accepted():
    from slr_wizard.config import SLRProjectionConfig, VALID_SCENARIOS
    for sc in VALID_SCENARIOS:
        cfg = SLRProjectionConfig(scenario=sc)
        errors = cfg.validate()
        assert errors == [], f"Scenario '{sc}' should be valid but got: {errors}"


def test_invalid_scenario_flagged():
    from slr_wizard.config import SLRProjectionConfig
    cfg = SLRProjectionConfig(scenario="super_extreme")
    errors = cfg.validate()
    assert any("scenario" in e.lower() for e in errors)


def test_valid_years_accepted():
    from slr_wizard.config import SLRProjectionConfig, VALID_YEARS
    for yr in VALID_YEARS:
        cfg = SLRProjectionConfig(target_year=yr)
        errors = cfg.validate()
        assert errors == [], f"Year {yr} should be valid"


def test_invalid_year_flagged():
    from slr_wizard.config import SLRProjectionConfig
    cfg = SLRProjectionConfig(target_year=2033)
    errors = cfg.validate()
    assert any("year" in e.lower() for e in errors)


def test_missing_dem_path_flagged():
    from slr_wizard.config import InputsConfig
    cfg = InputsConfig(dem_path="")
    errors = cfg.validate()
    assert any("dem_path" in e for e in errors)


def test_nonexistent_dem_path_flagged():
    from slr_wizard.config import InputsConfig
    cfg = InputsConfig(dem_path="/nonexistent/path/dem.tif")
    errors = cfg.validate()
    assert any("dem_path" in e for e in errors)


def test_to_dict_round_trip():
    from slr_wizard.config import SLRInundationConfig
    cfg = SLRInundationConfig()
    cfg.projection.scenario = "high"
    cfg.projection.target_year = 2100
    d = cfg.to_dict()
    cfg2 = SLRInundationConfig.from_dict(d)
    assert cfg2.projection.scenario == "high"
    assert cfg2.projection.target_year == 2100


def test_save_and_load_config(tmp_path):
    from slr_wizard.config import SLRInundationConfig, save_config, load_config
    cfg = SLRInundationConfig()
    cfg.projection.scenario = "extreme"
    cfg.output.output_prefix = "test_run"
    p = tmp_path / "test_config.json"
    save_config(cfg, p)
    assert p.exists()
    loaded = load_config(p)
    assert loaded.projection.scenario == "extreme"
    assert loaded.output.output_prefix == "test_run"


def test_validate_config_raises_on_invalid():
    from slr_wizard.config import SLRInundationConfig, InputsConfig, validate_config
    cfg = SLRInundationConfig(inputs=InputsConfig(dem_path=""))
    with pytest.raises(ValueError):
        validate_config(cfg)
