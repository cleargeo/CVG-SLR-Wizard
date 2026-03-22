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
from __future__ import annotations
import json
import pytest
from pathlib import Path
from slr_wizard.report import build_json_report, write_json_report, REPORT_SCHEMA_VERSION, CVG_HEADER, NOAA_REF
from slr_wizard.processing import InundationResult
from slr_wizard.config import SLRInundationConfig, InputsConfig, SLRProjectionConfig, ProcessingConfig, OutputConfig, RunMetadata


def _make_result(**kwargs):
    defaults = dict(run_id='test-001', scenario='intermediate', target_year=2050, slr_offset_ft=1.234, datum_shift_ft=0.0, water_surface_navd88_ft=1.234, inundated_cells=25, total_cells=100, inundated_area_m2=625.0, max_depth_ft=3.5, mean_depth_ft=1.2, elapsed_sec=4.5, qa_flags=[])
    defaults.update(kwargs)
    return InundationResult(**defaults)


def _make_config():
    return SLRInundationConfig(inputs=InputsConfig(dem_path='fake.tif', noaa_station_id='8724580'), projection=SLRProjectionConfig(scenario='intermediate', target_year=2050), processing=ProcessingConfig(connected_inundation=False), output=OutputConfig(output_dir='output_test'), metadata=RunMetadata(project_name='Test Project', analyst='Test Analyst'))


class TestBuildJsonReport:
    def test_returns_dict(self):
        assert isinstance(build_json_report(_make_result(), _make_config()), dict)

    def test_schema_version_present(self):
        assert build_json_report(_make_result(), _make_config())['schema_version'] == REPORT_SCHEMA_VERSION

    def test_tool_name_present(self):
        assert build_json_report(_make_result(), _make_config())['tool'] == 'CVG SLR Wizard'

    def test_tool_version_present(self):
        from slr_wizard import __version__
        assert build_json_report(_make_result(), _make_config())['tool_version'] == __version__

    def test_generated_utc_present(self):
        r = build_json_report(_make_result(), _make_config())
        assert 'generated_utc' in r and r['generated_utc'].endswith('Z')

    def test_copyright_present(self):
        r = build_json_report(_make_result(), _make_config())
        assert r['copyright'] == CVG_HEADER

    def test_references_is_list(self):
        r = build_json_report(_make_result(), _make_config())
        assert isinstance(r['references'], list) and len(r['references']) >= 1

    def test_references_contains_noaa(self):
        r = build_json_report(_make_result(), _make_config())
        assert NOAA_REF in r['references']

    def test_run_section_present(self):
        r = build_json_report(_make_result(), _make_config())
        assert 'run' in r and isinstance(r['run'], dict)

    def test_config_section_present(self):
        r = build_json_report(_make_result(), _make_config())
        assert 'config' in r and isinstance(r['config'], dict)

    def test_run_contains_run_id(self):
        r = build_json_report(_make_result(run_id='my-unique-run'), _make_config())
        assert r['run']['run_id'] == 'my-unique-run'

    def test_run_contains_scenario(self):
        r = build_json_report(_make_result(scenario='high'), _make_config())
        assert r['run']['scenario'] == 'high'

    def test_run_contains_inundated_pct(self):
        r = build_json_report(_make_result(inundated_cells=50, total_cells=100), _make_config())
        assert 'inundated_pct' in r['run']

    def test_extra_fields_merged(self):
        r = build_json_report(_make_result(), _make_config(), extra={'custom_key': 'custom_val'})
        assert r['custom_key'] == 'custom_val'

    def test_report_is_json_serializable(self):
        r = build_json_report(_make_result(), _make_config())
        assert isinstance(json.dumps(r), str)


class TestWriteJsonReport:
    def test_creates_file(self, tmp_path):
        pp = tmp_path / 'report.json'
        write_json_report(_make_result(), _make_config(), pp)
        assert pp.exists()

    def test_file_is_valid_json(self, tmp_path):
        pp = tmp_path / 'report.json'
        write_json_report(_make_result(), _make_config(), pp)
        data = json.loads(pp.read_text(encoding='utf-8'))
        assert isinstance(data, dict)

    def test_creates_parent_dirs(self, tmp_path):
        pp = tmp_path / 'sub' / 'deep' / 'report.json'
        write_json_report(_make_result(), _make_config(), pp)
        assert pp.exists()

    def test_written_report_has_schema_version(self, tmp_path):
        pp = tmp_path / 'report.json'
        write_json_report(_make_result(), _make_config(), pp)
        data = json.loads(pp.read_text(encoding='utf-8'))
        assert data['schema_version'] == REPORT_SCHEMA_VERSION


class TestInundationResultToDict:
    def test_to_dict_has_run_id(self):
        r = _make_result(run_id='abc')
        assert r.to_dict()['run_id'] == 'abc'

    def test_to_dict_inundated_pct_formula(self):
        r = _make_result(inundated_cells=25, total_cells=100)
        assert abs(r.to_dict()['inundated_pct'] - 25.0) < 0.01

    def test_to_dict_qa_flags_list(self):
        r = _make_result(qa_flags=['flag_a'])
        assert 'flag_a' in r.to_dict()['qa_flags']

    def test_inundated_pct_zero_when_no_cells(self):
        r = _make_result(inundated_cells=0, total_cells=0)
        assert r.inundated_pct == 0.0

    def test_slr_offset_ft_rounded_in_dict(self):
        r = _make_result(slr_offset_ft=1.23456789)
        assert r.to_dict()['slr_offset_ft'] == round(1.23456789, 4)
