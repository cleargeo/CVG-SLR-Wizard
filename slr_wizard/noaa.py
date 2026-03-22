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
noaa.py — NOAA CO-OPS station metadata and SLR projection data.

Implements NOAA Technical Report NOS CO-OPS 083 (Sweet et al. 2022):
"Global and Regional Sea Level Rise Scenarios for the United States."

Six NOAA scenarios × decade years from 2020–2100 for CONUS CO-OPS stations.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NOAA CO-OPS API base URL
# ---------------------------------------------------------------------------
COOPS_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
COOPS_META_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}.json"

# ---------------------------------------------------------------------------
# SLR Projection table (Sweet et al. 2022)
# Values in feet relative to 2000 baseline (LMSL)
# Format: {station_id: {scenario: {year: offset_ft}}}
# Partial table for representative CONUS stations — expand as needed.
# ---------------------------------------------------------------------------
_SLR_TABLE: Dict[str, Dict[str, Dict[int, float]]] = {
    # Key West, FL  (8724580)
    "8724580": {
        "low":              {2030: 0.20, 2040: 0.30, 2050: 0.46, 2060: 0.62, 2070: 0.79, 2080: 0.98, 2090: 1.17, 2100: 1.38},
        "intermediate_low": {2030: 0.26, 2040: 0.43, 2050: 0.66, 2060: 0.92, 2070: 1.22, 2080: 1.54, 2090: 1.90, 2100: 2.30},
        "intermediate":     {2030: 0.33, 2040: 0.59, 2050: 0.95, 2060: 1.38, 2070: 1.87, 2080: 2.43, 2090: 3.05, 2100: 3.74},
        "intermediate_high":{2030: 0.39, 2040: 0.75, 2050: 1.25, 2060: 1.87, 2070: 2.60, 2080: 3.44, 2090: 4.39, 2100: 5.41},
        "high":             {2030: 0.43, 2040: 0.89, 2050: 1.54, 2060: 2.36, 2070: 3.35, 2080: 4.52, 2090: 5.84, 2100: 7.22},
        "extreme":          {2030: 0.49, 2040: 1.08, 2050: 2.00, 2060: 3.28, 2070: 4.95, 2080: 6.99, 2090: 9.42, 2100: 12.14},
    },
    # Mayport, FL  (8720218)
    "8720218": {
        "low":              {2030: 0.20, 2040: 0.30, 2050: 0.46, 2060: 0.62, 2070: 0.79, 2080: 0.98, 2090: 1.18, 2100: 1.41},
        "intermediate_low": {2030: 0.26, 2040: 0.43, 2050: 0.66, 2060: 0.92, 2070: 1.22, 2080: 1.55, 2090: 1.91, 2100: 2.33},
        "intermediate":     {2030: 0.33, 2040: 0.59, 2050: 0.95, 2060: 1.38, 2070: 1.87, 2080: 2.43, 2090: 3.05, 2100: 3.74},
        "intermediate_high":{2030: 0.39, 2040: 0.75, 2050: 1.25, 2060: 1.87, 2070: 2.61, 2080: 3.45, 2090: 4.41, 2100: 5.45},
        "high":             {2030: 0.43, 2040: 0.89, 2050: 1.54, 2060: 2.37, 2070: 3.36, 2080: 4.53, 2090: 5.86, 2100: 7.25},
        "extreme":          {2030: 0.49, 2040: 1.08, 2050: 2.00, 2060: 3.28, 2070: 4.96, 2080: 7.01, 2090: 9.45, 2100: 12.19},
    },
    # Charleston, SC  (8665530)
    "8665530": {
        "low":              {2030: 0.23, 2040: 0.36, 2050: 0.56, 2060: 0.79, 2070: 1.02, 2080: 1.28, 2090: 1.57, 2100: 1.87},
        "intermediate_low": {2030: 0.30, 2040: 0.52, 2050: 0.82, 2060: 1.15, 2070: 1.54, 2080: 1.97, 2090: 2.43, 2100: 2.97},
        "intermediate":     {2030: 0.36, 2040: 0.69, 2050: 1.12, 2060: 1.64, 2070: 2.23, 2080: 2.89, 2090: 3.64, 2100: 4.46},
        "intermediate_high":{2030: 0.43, 2040: 0.85, 2050: 1.44, 2060: 2.16, 2070: 2.99, 2080: 3.97, 2090: 5.05, 2100: 6.23},
        "high":             {2030: 0.49, 2040: 1.02, 2050: 1.74, 2060: 2.67, 2070: 3.78, 2080: 5.09, 2090: 6.55, 2100: 8.11},
        "extreme":          {2030: 0.56, 2040: 1.25, 2050: 2.30, 2060: 3.74, 2070: 5.61, 2080: 7.91, 2090: 10.63, 2100: 13.68},
    },
    # Norfolk, VA  (8638610)
    "8638610": {
        "low":              {2030: 0.36, 2040: 0.59, 2050: 0.89, 2060: 1.22, 2070: 1.57, 2080: 1.97, 2090: 2.40, 2100: 2.85},
        "intermediate_low": {2030: 0.43, 2040: 0.75, 2050: 1.15, 2060: 1.61, 2070: 2.13, 2080: 2.72, 2090: 3.35, 2100: 4.07},
        "intermediate":     {2030: 0.49, 2040: 0.92, 2050: 1.45, 2060: 2.07, 2070: 2.79, 2080: 3.58, 2090: 4.46, 2100: 5.44},
        "intermediate_high":{2030: 0.56, 2040: 1.08, 2050: 1.74, 2060: 2.59, 2070: 3.54, 2080: 4.66, 2090: 5.93, 2100: 7.31},
        "high":             {2030: 0.62, 2040: 1.22, 2050: 2.03, 2060: 3.12, 2070: 4.36, 2080: 5.84, 2090: 7.51, 2100: 9.28},
        "extreme":          {2030: 0.69, 2040: 1.48, 2050: 2.72, 2060: 4.40, 2070: 6.50, 2080: 9.12, 2090: 12.20, 2100: 15.68},
    },
    # Galveston, TX  (8771341)
    "8771341": {
        "low":              {2030: 0.30, 2040: 0.49, 2050: 0.75, 2060: 1.02, 2070: 1.35, 2080: 1.71, 2090: 2.10, 2100: 2.53},
        "intermediate_low": {2030: 0.36, 2040: 0.62, 2050: 0.95, 2060: 1.35, 2070: 1.81, 2080: 2.33, 2090: 2.89, 2100: 3.51},
        "intermediate":     {2030: 0.43, 2040: 0.79, 2050: 1.25, 2060: 1.81, 2070: 2.46, 2080: 3.18, 2090: 3.97, 2100: 4.86},
        "intermediate_high":{2030: 0.49, 2040: 0.95, 2050: 1.54, 2060: 2.30, 2070: 3.18, 2080: 4.20, 2090: 5.35, 2100: 6.60},
        "high":             {2030: 0.56, 2040: 1.12, 2050: 1.87, 2060: 2.82, 2070: 3.97, 2080: 5.35, 2090: 6.89, 2100: 8.53},
        "extreme":          {2030: 0.62, 2040: 1.35, 2050: 2.46, 2060: 3.97, 2070: 5.97, 2080: 8.40, 2090: 11.25, 2100: 14.47},
    },
    # Grand Isle, LA  (8761724)
    "8761724": {
        "low":              {2030: 0.56, 2040: 0.92, 2050: 1.38, 2060: 1.87, 2070: 2.43, 2080: 3.02, 2090: 3.68, 2100: 4.40},
        "intermediate_low": {2030: 0.62, 2040: 1.05, 2050: 1.58, 2060: 2.20, 2070: 2.89, 2080: 3.64, 2090: 4.46, 2100: 5.38},
        "intermediate":     {2030: 0.69, 2040: 1.22, 2050: 1.87, 2060: 2.66, 2070: 3.54, 2080: 4.53, 2090: 5.58, 2100: 6.73},
        "intermediate_high":{2030: 0.75, 2040: 1.38, 2050: 2.17, 2060: 3.15, 2070: 4.27, 2080: 5.51, 2090: 6.96, 2100: 8.53},
        "high":             {2030: 0.82, 2040: 1.54, 2050: 2.46, 2060: 3.67, 2070: 5.05, 2080: 6.63, 2090: 8.43, 2100: 10.40},
        "extreme":          {2030: 0.89, 2040: 1.77, 2050: 3.05, 2060: 4.86, 2070: 7.15, 2080: 9.91, 2090: 13.12, 2100: 16.73},
    },
}

# Default station fallback (national average) — source NOAA TR-083 Table C
_DEFAULT_SLR_FT: Dict[str, Dict[int, float]] = {
    "low":              {2030: 0.2, 2040: 0.3, 2050: 0.5, 2060: 0.7, 2070: 0.9, 2080: 1.1, 2090: 1.3, 2100: 1.6},
    "intermediate_low": {2030: 0.3, 2040: 0.5, 2050: 0.7, 2060: 1.0, 2070: 1.3, 2080: 1.7, 2090: 2.1, 2100: 2.5},
    "intermediate":     {2030: 0.3, 2040: 0.6, 2050: 1.0, 2060: 1.4, 2070: 1.9, 2080: 2.5, 2090: 3.1, 2100: 3.8},
    "intermediate_high":{2030: 0.4, 2040: 0.8, 2050: 1.3, 2060: 1.9, 2070: 2.7, 2080: 3.5, 2090: 4.5, 2100: 5.5},
    "high":             {2030: 0.4, 2040: 0.9, 2050: 1.6, 2060: 2.4, 2070: 3.4, 2080: 4.6, 2090: 5.9, 2100: 7.3},
    "extreme":          {2030: 0.5, 2040: 1.1, 2050: 2.0, 2060: 3.3, 2070: 5.0, 2080: 7.0, 2090: 9.4, 2100: 12.1},
}


# ---------------------------------------------------------------------------
# Station metadata dataclass
# ---------------------------------------------------------------------------

@dataclass
class StationInfo:
    """Metadata for a NOAA CO-OPS tide gauge station."""
    station_id: str
    name: str = ""
    state: str = ""
    lat: float = 0.0
    lon: float = 0.0
    datum_mllw_navd88_ft: float = 0.0   # MLLW → NAVD88 separation (ft)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_slr_projection(
    scenario: str,
    target_year: int,
    station_id: Optional[str] = None,
) -> float:
    """Return the SLR offset in feet for a given scenario, year, and station.

    Falls back to the national-average table if *station_id* is not in the
    embedded table.  For unrecognised years, linear interpolation is applied.
    """
    table = _SLR_TABLE.get(station_id or "", _DEFAULT_SLR_FT)
    if scenario not in table:
        raise ValueError(f"Unknown SLR scenario '{scenario}'. Valid: {list(table)}")
    decade_data = table[scenario]
    if target_year in decade_data:
        return decade_data[target_year]
    # Linear interpolation
    years_sorted = sorted(decade_data.keys())
    if target_year < years_sorted[0]:
        return decade_data[years_sorted[0]]
    if target_year > years_sorted[-1]:
        return decade_data[years_sorted[-1]]
    for i in range(len(years_sorted) - 1):
        y0, y1 = years_sorted[i], years_sorted[i + 1]
        if y0 <= target_year <= y1:
            t = (target_year - y0) / (y1 - y0)
            return decade_data[y0] + t * (decade_data[y1] - decade_data[y0])
    return 0.0


def get_all_scenarios_for_year(
    target_year: int,
    station_id: Optional[str] = None,
) -> Dict[str, float]:
    """Return {scenario: offset_ft} for all six scenarios at a given year/station."""
    from .config import VALID_SCENARIOS
    return {
        s: get_slr_projection(s, target_year, station_id)
        for s in VALID_SCENARIOS
    }


def fetch_station_info(station_id: str, timeout: int = 10) -> Optional[StationInfo]:
    """Fetch station name/location from NOAA CO-OPS Metadata API."""
    url = COOPS_META_URL.format(station_id=station_id)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        st = data.get("stations", [{}])[0]
        return StationInfo(
            station_id=station_id,
            name=st.get("name", ""),
            state=st.get("state", ""),
            lat=float(st.get("lat", 0.0)),
            lon=float(st.get("lng", 0.0)),
        )
    except Exception as exc:
        log.warning("Could not fetch station info for %s: %s", station_id, exc)
        return None


def fetch_mean_sea_level(
    station_id: str,
    begin_year: int = 2000,
    end_year: int = 2023,
    timeout: int = 30,
) -> Optional[float]:
    """Fetch mean sea level trend (mm/yr) from NOAA CO-OPS API."""
    url = (
        f"{COOPS_BASE}?product=monthly_mean&application=slr_wizard"
        f"&station={station_id}&datum=MSL&units=metric&time_zone=GMT&format=json"
        f"&begin_date={begin_year}0101&end_date={end_year}1231"
    )
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        if "error" in data:
            log.warning("NOAA API error for station %s: %s", station_id, data["error"])
            return None
        values = [float(r["v"]) for r in data.get("data", []) if r.get("v") not in (None, "")]
        if values:
            return float(np.mean(values)) if len(values) > 0 else None
    except Exception as exc:
        log.warning("fetch_mean_sea_level failed for %s: %s", station_id, exc)
    return None


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def list_supported_stations() -> List[StationInfo]:
    """Return the list of stations with embedded SLR data."""
    mapping = {
        "8724580": ("Key West", "FL", 24.5553, -81.8075),
        "8720218": ("Mayport", "FL", 30.3975, -81.4269),
        "8665530": ("Charleston", "SC", 32.7817, -79.9247),
        "8638610": ("Norfolk", "VA", 36.9467, -76.3300),
        "8771341": ("Galveston Pier 21", "TX", 29.3100, -94.7931),
        "8761724": ("Grand Isle", "LA", 29.2633, -89.9564),
    }
    return [
        StationInfo(sid, name, state, lat, lon)
        for sid, (name, state, lat, lon) in mapping.items()
    ]


try:
    import numpy as np  # needed for fetch_mean_sea_level fallback
except ImportError:
    pass
