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
"""fetch_all_stations.py — Bulk fetch NOAA CO-OPS station metadata.

Queries the NOAA CO-OPS Metadata API for all active water level stations
and saves a curated JSON cache to ``slr_wizard/demo_data/noaa_stations.json``.

Usage::

    python tools/fetch_all_stations.py [--state FL] [--output PATH] [--dry-run]

Reference
---------
NOAA CO-OPS Metadata API:
  https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# NOAA CO-OPS Metadata API
_COOPS_STATIONS_URL = (
    "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
    "?type=waterlevels&status=active&units=metric"
)
_COOPS_DETAIL_URL = (
    "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{sid}/details.json"
)
_COOPS_SLR_URL = (
    "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{sid}/sealeveltrends.json"
)

# Project default output path
_DEFAULT_OUTPUT = Path(__file__).parent.parent / "slr_wizard" / "demo_data" / "noaa_stations.json"


def _get(url: str, timeout: int = 20) -> Any:
    """Fetch JSON from *url* and return parsed object."""
    log.debug("GET %s", url)
    with urllib.request.urlopen(url, timeout=timeout) as r:  # nosec
        return json.loads(r.read().decode("utf-8"))


def fetch_station_list(state_filter: Optional[str] = None) -> List[Dict]:
    """Return list of active water-level stations, optionally filtered by state."""
    data = _get(_COOPS_STATIONS_URL)
    stations = data.get("stations", [])
    if state_filter:
        sf = state_filter.upper()
        stations = [s for s in stations if s.get("state", "").upper() == sf]
    log.info("Found %d stations (filter: %s)", len(stations), state_filter or "none")
    return stations


def enrich_station(station: Dict, include_slr: bool = True) -> Dict:
    """Add detail + optional sea-level trend fields to a station record."""
    sid = station["id"]
    record = dict(station)

    try:
        detail = _get(_COOPS_DETAIL_URL.format(sid=sid), timeout=15)
        record.update({
            "lat": detail.get("lat"),
            "lon": detail.get("lng"),
            "timezone_offset": detail.get("timezonecorr"),
            "datum_msl": detail.get("datums", {}).get("MSL"),
            "datum_mhhw": detail.get("datums", {}).get("MHHW"),
            "datum_navd88": detail.get("datums", {}).get("NAVD"),
        })
    except Exception as exc:
        log.warning("Could not fetch detail for station %s: %s", sid, exc)

    if include_slr:
        try:
            trend = _get(_COOPS_SLR_URL.format(sid=sid), timeout=15)
            if trend.get("sealeveltrends"):
                t = trend["sealeveltrends"][0]
                record["slr_trend_mm_yr"] = t.get("linear")
                record["slr_trend_ci_mm_yr"] = t.get("ci95")
                record["slr_trend_start_yr"] = t.get("firstYear")
                record["slr_trend_end_yr"] = t.get("lastYear")
        except Exception as exc:
            log.warning("Could not fetch SLR trend for station %s: %s", sid, exc)

    return record


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bulk fetch NOAA CO-OPS station metadata for SLR Wizard."
    )
    parser.add_argument("--state", default=None, metavar="XX",
                        help="2-letter state code to filter stations (e.g. FL).")
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT), metavar="PATH",
                        help="Output JSON file path.")
    parser.add_argument("--no-slr", action="store_true",
                        help="Skip fetching sea-level trend data (faster).")
    parser.add_argument("--dry-run", action="store_true",
                        help="List stations only; do not fetch detail or write output.")
    parser.add_argument("--delay", type=float, default=0.25, metavar="SEC",
                        help="Seconds to wait between detail requests (default 0.25).")
    args = parser.parse_args(argv)

    stations = fetch_station_list(state_filter=args.state)

    if args.dry_run:
        for s in stations:
            print(f"  {s['id']:10s}  {s.get('name', ''):<40s}  {s.get('state', '')}")
        log.info("Dry run complete — %d stations listed.", len(stations))
        return 0

    enriched = []
    for i, s in enumerate(stations, 1):
        log.info("[%d/%d] Enriching station %s — %s", i, len(stations), s["id"], s.get("name", ""))
        enriched.append(enrich_station(s, include_slr=not args.no_slr))
        if args.delay > 0:
            time.sleep(args.delay)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        json.dump(enriched, fh, indent=2)
    log.info("Saved %d stations → %s", len(enriched), output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
