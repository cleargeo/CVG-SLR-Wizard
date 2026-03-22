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
paths.py — Canonical path resolution for the SLR Wizard.

All file/directory paths used by the package are resolved through this module
so that tests, CLI, and the web API all agree on locations.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Package root
# ---------------------------------------------------------------------------
PACKAGE_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = PACKAGE_DIR.parent

# ---------------------------------------------------------------------------
# Static assets bundled with the package
# ---------------------------------------------------------------------------
TEMPLATES_DIR: Path = PACKAGE_DIR / "templates"
DEMO_DATA_DIR: Path = PACKAGE_DIR / "demo_data"
CACHE_DIR: Path = PACKAGE_DIR / "cache"

# ---------------------------------------------------------------------------
# Runtime / user-facing directories (resolved relative to CWD or env var)
# ---------------------------------------------------------------------------


def get_output_dir(base: str | Path | None = None) -> Path:
    """Return the output directory, creating it if necessary."""
    if base:
        p = Path(base)
    else:
        p = Path(os.environ.get("SLR_OUTPUT_DIR", "output"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_cache_dir() -> Path:
    """Return the package-level cache directory."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def get_checkpoint_path(run_id: str, output_dir: str | Path | None = None) -> Path:
    """Return path for the checkpoint JSON file for *run_id*."""
    return get_output_dir(output_dir) / f"checkpoint_{run_id}.json"


def get_report_path(
    prefix: str,
    scenario: str,
    year: int,
    output_dir: str | Path | None = None,
    ext: str = "json",
) -> Path:
    """Construct a canonical output path for a report file."""
    stem = f"{prefix}_{scenario}_{year}"
    return get_output_dir(output_dir) / f"{stem}.{ext}"


def get_raster_path(
    prefix: str,
    scenario: str,
    year: int,
    layer: str = "depth",
    output_dir: str | Path | None = None,
) -> Path:
    """Construct a canonical output path for a GeoTIFF."""
    stem = f"{prefix}_{scenario}_{year}_{layer}"
    return get_output_dir(output_dir) / f"{stem}.tif"


def resolve_vdatum_jar() -> Path | None:
    """Locate the VDatum JAR, checking env var then common install paths."""
    env = os.environ.get("VDATUM_JAR")
    if env and Path(env).exists():
        return Path(env)
    candidates = [
        Path(r"C:\VDatum\vdatum.jar"),
        Path(r"C:\Program Files\VDatum\vdatum.jar"),
        Path.home() / "VDatum" / "vdatum.jar",
        PROJECT_ROOT.parent / "VDatum" / "vdatum.jar",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None
