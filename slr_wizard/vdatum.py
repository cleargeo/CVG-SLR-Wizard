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
vdatum.py — NOAA VDatum integration for the SLR Wizard.

Provides tidal datum conversions (MLLW ↔ NAVD88, MSL ↔ NAVD88, etc.)
via two paths:
  1. Local VDatum v4.5.1 JAR (preferred when available).
  2. NOAA VDatum REST API (fallback).
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from .paths import resolve_vdatum_jar

log = logging.getLogger(__name__)

VDATUM_API_BASE = "https://vdatum.noaa.gov/vdatumweb/api/convert"

# Datum string mappings for the VDatum REST API
_DATUM_API_MAP: Dict[str, str] = {
    "NAVD88": "NAVD88",
    "NGVD29": "NGVD29",
    "MLLW":   "MLLW",
    "MHW":    "MHW",
    "MSL":    "MSL",
    "MTL":    "MTL",
    "MHHW":   "MHHW",
}


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class DatumShiftResult:
    """Vertical datum separation value."""
    from_datum: str
    to_datum: str
    shift_ft: float             # positive = to_datum is higher than from_datum
    lat: float
    lon: float
    source: str = "api"         # "local" | "api" | "table"
    uncertainty_ft: float = 0.0


# ---------------------------------------------------------------------------
# NOAA VDatum REST API
# ---------------------------------------------------------------------------

def query_vdatum_api(
    lat: float,
    lon: float,
    from_datum: str = "MLLW",
    to_datum: str = "NAVD88",
    timeout: int = 15,
) -> Optional[DatumShiftResult]:
    """Query the NOAA VDatum REST API for a datum shift at a point."""
    params = {
        "region": "contiguous",
        "s_x": str(lon),
        "s_y": str(lat),
        "s_h_frame": "NAD83_2011",
        "s_v_frame": _DATUM_API_MAP.get(from_datum, from_datum),
        "s_vd_frame": _DATUM_API_MAP.get(from_datum, from_datum),
        "t_v_frame": _DATUM_API_MAP.get(to_datum, to_datum),
        "t_vd_frame": _DATUM_API_MAP.get(to_datum, to_datum),
        "s_vertical_unit": "m",
        "t_vertical_unit": "m",
        "input": f"{lon},{lat},0",
    }
    url = f"{VDATUM_API_BASE}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        if data.get("Status") == "0":
            shift_m = float(data.get("t_z", 0.0))
            return DatumShiftResult(
                from_datum=from_datum,
                to_datum=to_datum,
                shift_ft=shift_m * 3.28084,
                lat=lat,
                lon=lon,
                source="api",
            )
        log.warning("VDatum API returned non-zero status at (%.4f, %.4f): %s", lat, lon, data)
    except Exception as exc:
        log.warning("VDatum API query failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Local VDatum JAR
# ---------------------------------------------------------------------------

def query_vdatum_local(
    lat: float,
    lon: float,
    from_datum: str = "MLLW",
    to_datum: str = "NAVD88",
    java_exe: str = "java",
) -> Optional[DatumShiftResult]:
    """Query the local VDatum v4.5.1 JAR for a datum shift."""
    jar = resolve_vdatum_jar()
    if jar is None:
        log.debug("Local VDatum JAR not found; will fall back to API.")
        return None
    with tempfile.TemporaryDirectory() as tmp:
        in_file = Path(tmp) / "in.txt"
        out_dir = Path(tmp)
        in_file.write_text(f"{lon},{lat},0\n", encoding="utf-8")
        cmd = [
            java_exe, "-jar", str(jar),
            "ihorz:NAD83_2011", "ivert:" + from_datum,
            "ohorz:NAD83_2011", "overt:" + to_datum,
            "region:contiguous",
            "ivert_unit:m", "overt_unit:m",
            f"inFile:{in_file}",
            f"outDir:{out_dir}",
            "outFile:result.txt",
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
            out_file = out_dir / "result.txt"
            if out_file.exists():
                line = out_file.read_text(encoding="utf-8").strip().split("\n")[-1]
                parts = line.split(",")
                shift_m = float(parts[2])
                return DatumShiftResult(
                    from_datum=from_datum,
                    to_datum=to_datum,
                    shift_ft=shift_m * 3.28084,
                    lat=lat,
                    lon=lon,
                    source="local",
                )
        except Exception as exc:
            log.warning("Local VDatum query failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------

def get_datum_separation(
    lat: float,
    lon: float,
    from_datum: str,
    to_datum: str,
) -> DatumShiftResult:
    """Return datum separation, preferring local VDatum then REST API."""
    result = query_vdatum_local(lat, lon, from_datum, to_datum)
    if result is not None:
        return result
    result = query_vdatum_api(lat, lon, from_datum, to_datum)
    if result is not None:
        return result
    log.error(
        "Could not obtain datum shift %s→%s at (%.4f, %.4f). Returning 0.",
        from_datum, to_datum, lat, lon,
    )
    return DatumShiftResult(
        from_datum=from_datum,
        to_datum=to_datum,
        shift_ft=0.0,
        lat=lat,
        lon=lon,
        source="fallback",
    )


def get_mllw_navd88_shift(lat: float, lon: float) -> float:
    """Convenience: return MLLW → NAVD88 shift in feet."""
    return get_datum_separation(lat, lon, "MLLW", "NAVD88").shift_ft


def get_msl_navd88_shift(lat: float, lon: float) -> float:
    """Convenience: return MSL → NAVD88 shift in feet."""
    return get_datum_separation(lat, lon, "MSL", "NAVD88").shift_ft


def get_ngvd29_navd88_shift(lat: float, lon: float) -> float:
    """Convenience: return NGVD29 → NAVD88 shift in feet."""
    return get_datum_separation(lat, lon, "NGVD29", "NAVD88").shift_ft
