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
"""_check_external.py — Quick connectivity check for all SLR Wizard external dependencies.

Run from the project root::

    python tools/_check_external.py

Exit code 0 = all checks passed; non-zero = at least one failure.
"""

from __future__ import annotations

import sys
import urllib.request
from typing import List, Tuple

PASS = "\u2705"
FAIL = "\u274c"
WARN = "\u26a0\ufe0f"


def _check(label: str, fn) -> bool:
    try:
        fn()
        print(f"  {PASS}  {label}")
        return True
    except Exception as exc:
        print(f"  {FAIL}  {label}  →  {exc}")
        return False


def check_noaa_coops_meta() -> None:
    """NOAA CO-OPS station metadata API (Key West 8724580)."""
    url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/8724580/details.json"
    with urllib.request.urlopen(url, timeout=10) as r:
        assert r.status == 200, f"HTTP {r.status}"


def check_noaa_coops_slr() -> None:
    """NOAA CO-OPS Sea Level Trends API (Key West 8724580)."""
    url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/8724580/sealeveltrends.json"
    with urllib.request.urlopen(url, timeout=10) as r:
        assert r.status == 200, f"HTTP {r.status}"


def check_noaa_tr083_scenarios() -> None:
    """NOAA Technical Report 083 scenario endpoint (public CSV index)."""
    url = "https://oceanservice.noaa.gov/hazards/sealevelrise/sealevelrise-tech-report.html"
    with urllib.request.urlopen(url, timeout=15) as r:
        assert r.status == 200, f"HTTP {r.status}"


def check_slr_wizard_import() -> None:
    """slr_wizard package imports cleanly."""
    import slr_wizard  # noqa: F401
    from slr_wizard import noaa, config, processing, insights  # noqa: F401


def check_slr_wizard_version() -> None:
    """slr_wizard has a version string."""
    import slr_wizard
    v = getattr(slr_wizard, "__version__", None)
    assert v, "No __version__ attribute found"
    print(f"       version: {v}", end="")


def check_reportlab() -> None:
    """reportlab PDF library is importable."""
    from reportlab.pdfgen import canvas  # noqa: F401


def check_rasterio() -> None:
    """rasterio geospatial raster library is importable."""
    import rasterio  # noqa: F401


def check_shapely() -> None:
    """shapely geometry library is importable."""
    from shapely.geometry import Point  # noqa: F401


def check_httpx() -> None:
    """httpx async HTTP client is importable."""
    import httpx  # noqa: F401


def check_fastapi() -> None:
    """FastAPI web framework is importable."""
    import fastapi  # noqa: F401


def main() -> int:
    print("\n========================================")
    print("  CVG SLR Wizard — External Checks")
    print("========================================\n")

    checks: List[Tuple[str, object]] = [
        ("NOAA CO-OPS station metadata API", check_noaa_coops_meta),
        ("NOAA CO-OPS sea level trends API", check_noaa_coops_slr),
        ("NOAA TR-083 scenario page", check_noaa_tr083_scenarios),
        ("slr_wizard package import", check_slr_wizard_import),
        ("slr_wizard version string", check_slr_wizard_version),
        ("reportlab (PDF generation)", check_reportlab),
        ("rasterio (raster I/O)", check_rasterio),
        ("shapely (geometry)", check_shapely),
        ("httpx (async HTTP)", check_httpx),
        ("fastapi (web API)", check_fastapi),
    ]

    results = []
    for label, fn in checks:
        results.append(_check(label, fn))

    passed = sum(results)
    total = len(results)
    print(f"\n{'='*40}")
    print(f"  {passed}/{total} checks passed")
    print(f"{'='*40}\n")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
