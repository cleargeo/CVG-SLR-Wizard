# =============================================================================
# CVG SLR Wizard — Portal Dashboard Application
# Clearview Geographic LLC — Proprietary and Confidential
# ADF Build: 1.0.x | FastAPI + Jinja2 | Python 3.10+
# =============================================================================
"""
Lightweight dashboard portal for the CVG SLR Wizard.

Provides a browser-based UI that proxies and aggregates data from the
SLR Wizard REST API (running on port 8010 by default). Shows:
  - API health / version status
  - Recent projection history (in-memory, last 50 runs)
  - Live SLR projection form
  - Supported NOAA stations table
  - Engineering insights KB browser

Environment variables
---------------------
SLRW_API_URL  Base URL of the SLR Wizard API (default: http://localhost:8010)
PORT          Listening port for this portal (default: 8030)
"""

from __future__ import annotations

import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SLRW_API_URL: str = os.environ.get("SLRW_API_URL", "http://localhost:8010").rstrip("/")
PORTAL_VERSION: str = "1.0.0"
MAX_HISTORY: int = 50

# ---------------------------------------------------------------------------
# In-memory run history
# ---------------------------------------------------------------------------
_history: Deque[Dict[str, Any]] = deque(maxlen=MAX_HISTORY)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CVG SLR Wizard Portal",
    description="Dashboard for the CVG Sea Level Rise Wizard API",
    version=PORTAL_VERSION,
    docs_url="/api-docs",
)

# Templates (co-located templates/ directory)
_TMPL_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_TMPL_DIR)


# ---------------------------------------------------------------------------
# HTTP client factory
# ---------------------------------------------------------------------------
def _slrw_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=SLRW_API_URL, timeout=15.0)


# ---------------------------------------------------------------------------
# Helper: safe API call
# ---------------------------------------------------------------------------
async def _api_get(path: str) -> tuple[Optional[Dict], Optional[str]]:
    """Return (data, error_str). On failure data=None."""
    try:
        async with _slrw_client() as client:
            r = await client.get(path)
            r.raise_for_status()
            return r.json(), None
    except httpx.ConnectError:
        return None, f"Cannot connect to SLR Wizard API at {SLRW_API_URL}"
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main portal dashboard."""
    health, health_err = await _api_get("/health")
    stations, _ = await _api_get("/api/stations")

    ctx = {
        "request": request,
        "api_url": SLRW_API_URL,
        "portal_version": PORTAL_VERSION,
        "api_health": health,
        "api_error": health_err,
        "stations": (stations or {}).get("stations", []),
        "station_count": (stations or {}).get("count", 0),
        "history": list(_history),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return templates.TemplateResponse("dashboard.html", ctx)


@app.get("/api/proxy/health")
async def proxy_health():
    """Forward health check to the SLR Wizard API."""
    data, err = await _api_get("/health")
    if err:
        return JSONResponse({"error": err}, status_code=503)
    return data


@app.get("/api/proxy/stations")
async def proxy_stations():
    """Forward stations list from the SLR Wizard API."""
    data, err = await _api_get("/api/stations")
    if err:
        return JSONResponse({"error": err}, status_code=503)
    return data


@app.get("/api/proxy/project")
async def proxy_project(
    station_id: str = "8724580",
    year: int = 2070,
    scenario: str = "Intermediate",
    baseline_datum: str = "NAVD88",
):
    """Proxy a projection request and record it in history."""
    path = (
        f"/api/project?station_id={station_id}&year={year}"
        f"&scenario={scenario}&baseline_datum={baseline_datum}"
    )
    data, err = await _api_get(path)
    if err:
        return JSONResponse({"error": err}, status_code=503)

    # Record in run history
    _history.appendleft({
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "station_id": station_id,
        "year": year,
        "scenario": scenario,
        "datum": baseline_datum,
        "slr_m": (data or {}).get("slr_m"),
        "slr_ft": (data or {}).get("slr_ft"),
        "ok": data is not None,
    })
    return data


@app.get("/api/proxy/insights")
async def proxy_insights(query: str = ""):
    """Proxy insights search from the SLR Wizard API."""
    path = f"/api/insights?query={query}" if query else "/api/insights"
    data, err = await _api_get(path)
    if err:
        return JSONResponse({"error": err}, status_code=503)
    return data


@app.get("/api/history")
async def get_history():
    """Return in-memory run history."""
    return {"count": len(_history), "runs": list(_history)}


@app.delete("/api/history")
async def clear_history():
    """Clear the in-memory run history."""
    _history.clear()
    return {"cleared": True}


@app.get("/health")
async def health():
    return {
        "service": "cvg-slr-wizard-portal",
        "version": PORTAL_VERSION,
        "status": "ok",
        "api_target": SLRW_API_URL,
        "ts": time.time(),
    }
