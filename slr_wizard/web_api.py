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
# License     : Proprietary -- CVG-ADF
# =============================================================================
"""
web_api.py — FastAPI application for the CVG SLR Wizard.

Endpoints:
  GET  /                     — Health check / version
  GET  /api/stations          — List supported NOAA stations
  GET  /api/project           — Quick SLR projection lookup (no DEM)
  POST /api/run               — Run inundation analysis (JSON config)
  GET  /api/insights          — Search knowledge base
  GET  /api/insights/{topic}  — Get specific topic guidance
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Query, UploadFile, File
    from fastapi.responses import JSONResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    _FASTAPI_OK = True
except ImportError:
    _FASTAPI_OK = False
    log.warning("fastapi/pydantic not installed — web API disabled.")


if _FASTAPI_OK:

    class ProjectionRequest(BaseModel):
        station_id: Optional[str] = None
        scenario: str = "intermediate"
        target_year: int = 2050

    class RunConfigPayload(BaseModel):
        dem_path: str
        noaa_station_id: Optional[str] = None
        scenario: str = "intermediate"
        target_year: int = 2050
        output_dir: str = "output"
        connected_inundation: bool = True
        min_depth_ft: float = 0.0
        custom_slr_offset_ft: Optional[float] = None
        output_prefix: str = "slr_inundation"
        project_name: str = ""
        analyst: str = ""

    def create_app() -> "FastAPI":
        from . import __version__
        app = FastAPI(
            title="CVG SLR Wizard API",
            description="Sea Level Rise Inundation Grid Wizard — Clearview Geographic LLC",
            version=__version__,
            contact={"name": "Alex Zelenski, GISP", "email": "azelenski@clearviewgeographic.com"},
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        _register_routes(app)
        return app

    def _register_routes(app: "FastAPI") -> None:

        @app.get("/")
        async def root():
            from . import __version__
            return {
                "tool": "CVG SLR Wizard",
                "version": __version__,
                "status": "ok",
                "copyright": "© Clearview Geographic LLC",
            }

        @app.get("/api/stations")
        async def stations():
            from .noaa import list_supported_stations
            return [
                {"station_id": s.station_id, "name": s.name,
                 "state": s.state, "lat": s.lat, "lon": s.lon}
                for s in list_supported_stations()
            ]

        @app.get("/api/project")
        async def project(
            year: int = Query(2050, description="Target year"),
            scenario: str = Query("intermediate", description="SLR scenario name"),
            station_id: Optional[str] = Query(None, description="NOAA CO-OPS station ID"),
        ):
            from .noaa import get_all_scenarios_for_year, get_slr_projection
            from .insights import get_scenario_description
            try:
                all_sc = get_all_scenarios_for_year(year, station_id)
                return {
                    "year": year,
                    "station_id": station_id or "national_avg",
                    "scenarios": {
                        sc: {
                            "ft": round(ft, 3),
                            "m": round(ft / 3.28084, 3),
                            "description": get_scenario_description(sc),
                        }
                        for sc, ft in all_sc.items()
                    },
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @app.post("/api/run")
        async def run(payload: RunConfigPayload):
            from .config import (
                SLRInundationConfig, InputsConfig, SLRProjectionConfig,
                ProcessingConfig, OutputConfig, RunMetadata, validate_config,
            )
            from .processing import run_inundation
            from .report import build_json_report

            cfg = SLRInundationConfig(
                inputs=InputsConfig(
                    dem_path=payload.dem_path,
                    noaa_station_id=payload.noaa_station_id or "",
                    custom_slr_offset_ft=payload.custom_slr_offset_ft,
                ),
                projection=SLRProjectionConfig(
                    scenario=payload.scenario,
                    target_year=payload.target_year,
                ),
                processing=ProcessingConfig(
                    connected_inundation=payload.connected_inundation,
                    min_depth_ft=payload.min_depth_ft,
                ),
                output=OutputConfig(
                    output_dir=payload.output_dir,
                    output_prefix=payload.output_prefix,
                ),
                metadata=RunMetadata(
                    project_name=payload.project_name,
                    analyst=payload.analyst,
                ),
            )
            try:
                validate_config(cfg)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

            try:
                result = run_inundation(cfg, resume=False)
                return build_json_report(result, cfg)
            except Exception as e:
                log.exception("Run failed")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/insights")
        async def insights(q: str = Query("", description="Search query")):
            from .insights import search_insights
            results = search_insights(q)
            return [r.to_dict() for r in results]

        @app.get("/api/insights/{topic}")
        async def insight_topic(topic: str):
            from .insights import get_guidance
            entry = get_guidance(topic)
            if entry is None:
                raise HTTPException(status_code=404, detail=f"Topic not found: {topic}")
            return entry.to_dict()

        @app.get(
            "/api/wizards/status",
            summary="Status of all CVG Wizard subsystems",
            tags=["ops"],
        )
        async def wizards_status():
            import sys, os, datetime
            def _probe(pkg, path):
                try:
                    root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), path)
                    if root not in sys.path:
                        sys.path.insert(0, root)
                    mod = __import__(pkg)
                    return {"available": True, "version": getattr(mod, "__version__", "unknown"), "error": None}
                except Exception as exc:
                    return {"available": False, "version": None, "error": str(exc)}
            try:
                from slr_wizard import __version__ as _v
            except Exception:
                _v = "unknown"
            return {
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "wizards": {
                    "slr_wizard": {"available": True, "version": _v, "error": None, "default_port": 8001,
                        "endpoints": ["GET /", "GET /health", "GET /api/stations", "GET /api/project",
                                      "POST /api/run", "GET /api/insights", "GET /api/insights/{topic}",
                                      "GET /api/storms/active", "GET /api/tides/current/{station_id}",
                                      "GET /api/idf", "GET /api/wizards/status"]},
                    "storm_surge_wizard": {**_probe("storm_surge_wizard", "CVG_Storm Surge Wizard"), "default_port": 8080},
                    "rainfall_wizard": {**_probe("rainfall_wizard", "CVG_Rainfall Wizard"), "default_port": 8002},
                },
            }

        # ── /health ──────────────────────────────────────────────────────────

        @app.get("/health", summary="Liveness probe", tags=["ops"])
        async def health():
            """Return service status and version (used by Caddy health_uri checks)."""
            import datetime
            from slr_wizard import __version__ as _v
            return {
                "status": "ok",
                "service": "CVG SLR Wizard",
                "version": _v,
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        # ── /api/storms/active ────────────────────────────────────────────────

        @app.get(
            "/api/storms/active",
            summary="Active NHC tropical storms",
            tags=["nhc"],
        )
        async def active_storms(timeout: float = 20.0):
            """Proxy the NHC CurrentStorms.json feed — returns active storms or empty list."""
            import urllib.request, json as _json
            NHC_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"
            try:
                req = urllib.request.Request(NHC_URL, headers={"User-Agent": "CVG-SLR-Wizard/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = _json.loads(resp.read())
                raw = data.get("activeStorms", [])
                storms = []
                for s in (raw if isinstance(raw, list) else []):
                    storms.append({
                        "id":             s.get("id"),
                        "name":           s.get("name"),
                        "classification": s.get("classification"),
                        "intensity":      s.get("intensity"),
                        "lat":            s.get("lat"),
                        "lon":            s.get("lon"),
                        "advisory_url":   s.get("advisoryUrl") or s.get("advisoryurl"),
                    })
                return storms
            except Exception as exc:
                log.warning("NHC feed unavailable: %s", exc)
                return []

        # ── /api/tides/current/{station_id} ───────────────────────────────────

        @app.get(
            "/api/tides/current/{station_id}",
            summary="Live NOAA CO-OPS water level",
            tags=["tides"],
        )
        async def tides_current(station_id: str, datum: str = "NAVD", units: str = "feet"):
            """Fetch the latest observed water level from NOAA CO-OPS for a station.

            Parameters
            ----------
            station_id: NOAA CO-OPS station (e.g. 8724580 for Key West).
            datum:      Vertical datum — NAVD, MLLW, MSL, etc. (default NAVD).
            units:      feet or metric (default feet).
            """
            import urllib.request, json as _json, datetime as _dt
            end   = _dt.datetime.utcnow()
            begin = end - _dt.timedelta(hours=1)
            fmt   = "%Y%m%d %H:%M"
            url = (
                "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
                f"?begin_date={begin.strftime(fmt)}&end_date={end.strftime(fmt)}"
                f"&station={station_id}&product=water_level&datum={datum}"
                f"&time_zone=GMT&units={units}&application=CVG_SLR_Wizard&format=json"
            )
            try:
                with urllib.request.urlopen(url, timeout=15) as resp:
                    data = _json.loads(resp.read())
                if "error" in data:
                    raise HTTPException(status_code=404, detail=data["error"].get("message", "Station not found"))
                obs = data.get("data", [])
                latest = obs[-1] if obs else None
                return {
                    "station_id": station_id,
                    "datum": datum,
                    "units": units,
                    "latest_observation": latest,
                    "observation_count": len(obs),
                    "source": "NOAA CO-OPS",
                }
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"CO-OPS API error: {exc}") from exc

        # ── /api/idf ─────────────────────────────────────────────────────────

        @app.get(
            "/api/idf",
            summary="IDF table for a tide station / design scenario",
            tags=["slr"],
        )
        async def idf_table(
            station_id: str = Query("8724580", description="NOAA CO-OPS station ID"),
            target_year: int = Query(2050, description="Planning horizon year"),
        ):
            """Return SLR projections across all 6 scenarios for a station/year — formatted as an IDF-style table.

            Useful for generating scenario comparison matrices for reports.
            """
            from .noaa import get_all_scenarios_for_year
            try:
                all_sc = get_all_scenarios_for_year(target_year, station_id)
                rows = []
                for sc, ft in all_sc.items():
                    rows.append({
                        "scenario": sc,
                        "slr_ft": round(ft, 3),
                        "slr_m": round(ft / 3.28084, 3),
                        "slr_in": round(ft * 12.0, 2),
                    })
                return {
                    "station_id": station_id,
                    "target_year": target_year,
                    "reference": "NOAA Technical Report NOS CO-OPS 083 (Sweet et al. 2022)",
                    "scenarios": rows,
                }
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc


else:
    def create_app():
        raise ImportError("fastapi and pydantic are required: pip install fastapi pydantic")

