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
web.py -- FastAPI HTML web interface for the CVG SLR Wizard.

Provides a public-facing multi-step wizard UI (HTML form) that renders
Jinja2 templates and a FastAPI app serving them.  This is separate from
web_api.py (JSON REST API) and focuses on the browser-based user experience.

Routes
------
GET  /           -- Wizard input form (index.html)
POST /project    -- Projection result page (result.html)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, Form, Request
    from fastapi.responses import HTMLResponse
    from fastapi.templating import Jinja2Templates
    _FASTAPI_OK = True
except ImportError:
    _FASTAPI_OK = False
    log.warning("fastapi not installed -- web UI disabled.")

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    _JINJA2_OK = True
except ImportError:
    _JINJA2_OK = False
    log.warning("jinja2 not installed -- HTML rendering disabled.")

from .paths import TEMPLATES_DIR
from . import __version__


# ---------------------------------------------------------------------------
# Jinja2 standalone render helpers
# ---------------------------------------------------------------------------

_JINJA2_ENV = None

def _get_env():
    global _JINJA2_ENV
    if not _JINJA2_OK:
        return None
    if _JINJA2_ENV is not None:
        return _JINJA2_ENV
    if not TEMPLATES_DIR.exists():
        log.warning("Templates directory not found: %s", TEMPLATES_DIR)
        return None
    _JINJA2_ENV = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return _JINJA2_ENV

def render_template(template_name, context):
    env = _get_env()
    if env is None:
        return str(template_name)
    ctx = dict(tool_version=__version__, version=__version__)
    ctx.update(context)
    try:
        return env.get_template(template_name).render(**ctx)
    except Exception as exc:
        log.error(str(exc))
        return str(exc)

def render_index(context=None):
    return render_template("index.html", context or {})


def render_result(result_dict, context=None):
    ctx = context or {}
    ctx["result"] = result_dict
    return render_template("result.html", ctx)


def render_error(message, context=None):
    ctx = context or {}
    ctx["error_message"] = message
    return render_template("error.html", ctx)

# ---------------------------------------------------------------------------
# FastAPI web application
# ---------------------------------------------------------------------------

if _FASTAPI_OK:
    _TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))

    def create_web_app():
        """Create and return the FastAPI web UI application."""
        from .engine import get_slr_projection, list_slr_scenarios, list_slr_stations, get_slr_sensitivity

        app = FastAPI(
            title="CVG SLR Wizard Web",
            description="Sea Level Rise Projection Web UI -- Clearview Geographic LLC",
            version=__version__,
        )

        @app.get("/", response_class=HTMLResponse)
        async def landing(request: Request):
            """Marketing landing page — product overview for the SLR Wizard."""
            return _TEMPLATES.TemplateResponse(
                request,
                "landing.html",
                {"request": request, "version": __version__},
            )

        @app.get("/wizard", response_class=HTMLResponse)
        async def index(request: Request):
            """Serve the projection wizard input form."""
            return _TEMPLATES.TemplateResponse(
                request,
                "index.html",
                {
                    "request": request,
                    "stations": list_slr_stations(),
                    "scenarios": list_slr_scenarios(),
                    "version": __version__,
                },
            )

        @app.post("/project", response_class=HTMLResponse)
        async def project(
            request: Request,
            station_id: str = Form("8724580"),
            scenario: str = Form("intermediate"),
            target_year: int = Form(2070),
        ):
            """Process the form and render the projection result page."""
            try:
                slr_m = get_slr_projection(
                    station_id,
                    target_year=target_year,
                    scenario=scenario,
                )
                all_sc = get_slr_sensitivity(station_id, target_year=target_year)
                stations = list_slr_stations()
                station_info = next(
                    (s for s in stations if s["station_id"] == station_id),
                    {"name": station_id, "region": "Unknown"},
                )
                all_scenarios_display = {
                    k: {"m": round(v, 4), "ft": round(v * 3.28084, 4)}
                    for k, v in all_sc.items()
                }
                return _TEMPLATES.TemplateResponse(
                    request,
                    "result.html",
                    {
                        "request": request,
                        "station_id": station_id,
                        "station_name": station_info["name"],
                        "station_region": station_info.get("region", ""),
                        "scenario": scenario,
                        "year": target_year,
                        "slr_m": round(slr_m, 4),
                        "slr_ft": round(slr_m * 3.28084, 4),
                        "all_scenarios": all_scenarios_display,
                        "version": __version__,
                    },
                )
            except Exception as exc:
                log.error("Projection failed: %s", exc)
                return _TEMPLATES.TemplateResponse(
                    request,
                    "result.html",
                    {"request": request, "error": str(exc), "version": __version__},
                    status_code=400,
                )

        @app.get("/health")
        async def health():
            """Liveness probe for Caddy health checks and Docker healthcheck."""
            return {"status": "ok", "service": "CVG SLR Wizard", "version": __version__}

        return app

    app = create_web_app()

else:
    def create_web_app():
        raise ImportError("fastapi is required: pip install fastapi")
