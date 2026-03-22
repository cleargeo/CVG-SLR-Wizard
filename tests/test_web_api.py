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
import pytest
pytest.importorskip('fastapi', reason='fastapi not installed')
pytest.importorskip('httpx', reason='httpx not installed')
from fastapi.testclient import TestClient
from slr_wizard.web_api import create_app


@pytest.fixture(scope='module')
def client():
    app = create_app()
    return TestClient(app)


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        assert client.get('/').status_code == 200

    def test_root_tool_name(self, client):
        assert client.get('/').json()['tool'] == 'CVG SLR Wizard'

    def test_root_status_ok(self, client):
        assert client.get('/').json()['status'] == 'ok'

    def test_root_has_version(self, client):
        assert 'version' in client.get('/').json()

    def test_root_has_copyright(self, client):
        assert 'copyright' in client.get('/').json()


class TestStationsEndpoint:
    def test_stations_returns_200(self, client):
        assert client.get('/api/stations').status_code == 200

    def test_stations_returns_list(self, client):
        assert isinstance(client.get('/api/stations').json(), list)

    def test_stations_list_not_empty(self, client):
        assert len(client.get('/api/stations').json()) > 0

    def test_stations_have_required_keys(self, client):
        for s in client.get('/api/stations').json():
            for k in ('station_id', 'name', 'state', 'lat', 'lon'):
                assert k in s

    def test_stations_lat_lon_are_numeric(self, client):
        for s in client.get('/api/stations').json():
            assert isinstance(s['lat'], (int, float))
            assert isinstance(s['lon'], (int, float))


class TestProjectEndpoint:
    def test_project_returns_200(self, client):
        assert client.get('/api/project?year=2050').status_code == 200

    def test_project_response_has_year(self, client):
        assert client.get('/api/project?year=2050').json()['year'] == 2050

    def test_project_response_has_scenarios(self, client):
        assert 'scenarios' in client.get('/api/project?year=2050').json()

    def test_project_scenarios_is_dict(self, client):
        assert isinstance(client.get('/api/project?year=2050').json()['scenarios'], dict)

    def test_project_scenarios_have_ft_and_m(self, client):
        for sc, d in client.get('/api/project?year=2050').json()['scenarios'].items():
            assert 'ft' in d and 'm' in d

    def test_project_with_station_id(self, client):
        r = client.get('/api/project?year=2050&station_id=8724580')
        assert r.status_code == 200 and r.json()['station_id'] == '8724580'

    def test_project_national_avg_when_no_station(self, client):
        assert client.get('/api/project?year=2050').json()['station_id'] == 'national_avg'


class TestInsightsEndpoint:
    def test_insights_returns_200(self, client):
        assert client.get('/api/insights').status_code == 200

    def test_insights_returns_list(self, client):
        assert isinstance(client.get('/api/insights').json(), list)

    def test_insights_with_query_returns_200(self, client):
        assert client.get('/api/insights?q=sea+level').status_code == 200


class TestWizardsStatusEndpoint:
    def test_status_returns_200(self, client):
        assert client.get('/api/wizards/status').status_code == 200

    def test_status_has_timestamp(self, client):
        assert 'timestamp_utc' in client.get('/api/wizards/status').json()

    def test_status_has_wizards_dict(self, client):
        r = client.get('/api/wizards/status').json()
        assert 'wizards' in r and isinstance(r['wizards'], dict)

    def test_status_includes_slr_wizard(self, client):
        assert 'slr_wizard' in client.get('/api/wizards/status').json()['wizards']

    def test_slr_wizard_is_available(self, client):
        r = client.get('/api/wizards/status').json()
        assert r['wizards']['slr_wizard']['available'] is True


class TestRunEndpoint:
    def test_run_missing_dem_path_returns_422(self, client):
        assert client.post('/api/run', json={}).status_code == 422

    def test_run_empty_dem_path_triggers_error(self, client):
        r = client.post('/api/run', json={'dem_path': '', 'scenario': 'intermediate', 'target_year': 2050})
        assert r.status_code in (422, 500)

    def test_run_invalid_scenario_returns_error(self, client):
        r = client.post('/api/run', json={'dem_path': 'fake.tif', 'scenario': 'super_duper_extreme', 'target_year': 2050})
        assert r.status_code in (422, 500)

    def test_run_invalid_year_returns_error(self, client):
        r = client.post('/api/run', json={'dem_path': 'fake.tif', 'scenario': 'intermediate', 'target_year': 1900})
        assert r.status_code in (422, 500)

    def test_run_valid_payload_not_rejected_by_pydantic(self, client):
        r = client.post('/api/run', json={'dem_path': 'nonexistent.tif', 'scenario': 'intermediate', 'target_year': 2050})
        assert r.status_code != 422, f'Pydantic rejected valid payload: {r.json()}'

    def test_run_accepts_optional_station_id(self, client):
        r = client.post('/api/run', json={'dem_path': 'nonexistent.tif', 'noaa_station_id': '8724580', 'scenario': 'intermediate', 'target_year': 2050})
        assert r.status_code != 422

    def test_run_accepts_custom_slr_override(self, client):
        r = client.post('/api/run', json={'dem_path': 'nonexistent.tif', 'scenario': 'intermediate', 'target_year': 2050, 'custom_slr_offset_ft': 2.5})
        assert r.status_code != 422
