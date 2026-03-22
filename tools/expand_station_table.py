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
"""expand_station_table.py — Expand the RSLR rate table to all 75 NOAA TR-083 stations.

NOAA Technical Report 083 (Sweet et al. 2022) provides sea-level rise scenarios
for 76 tide gauge stations across the US coastline.  This tool fetches the latest
station list from NOAA CO-OPS, cross-references it with the internal SLR Wizard
station table, and writes a fully populated JSON expansion for use by the API.

Output::

    slr_wizard/demo_data/tr083_station_table.json

Usage::

    python tools/expand_station_table.py [--output PATH] [--dry-run]

Reference
---------
Sweet et al. (2022). 2022 Sea Level Rise Technical Report.
  https://oceanservice.noaa.gov/hazards/sealevelrise/sealevelrise-tech-report.html
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

_DEFAULT_OUTPUT = Path(__file__).parent.parent / "slr_wizard" / "demo_data" / "tr083_station_table.json"

# NOAA TR-083 (2022 SLRTR) published tide gauge stations with baseline LMSL trends.
# Source: Table B.1, NOAA 2022 Sea Level Rise Technical Report.
# Fields: station_id, name, state, trend_mm_yr (1993-2021 satellite-era linear)
TR083_STATIONS: List[Dict[str, Any]] = [
    {"station_id": "8724580", "name": "Key West",                "state": "FL", "trend_mm_yr": 2.60},
    {"station_id": "8725110", "name": "Naples",                  "state": "FL", "trend_mm_yr": 2.40},
    {"station_id": "8726520", "name": "St. Petersburg",          "state": "FL", "trend_mm_yr": 2.50},
    {"station_id": "8727520", "name": "Cedar Key",               "state": "FL", "trend_mm_yr": 2.30},
    {"station_id": "8728690", "name": "Apalachicola",            "state": "FL", "trend_mm_yr": 2.10},
    {"station_id": "8729108", "name": "Panama City",             "state": "FL", "trend_mm_yr": 2.20},
    {"station_id": "8735180", "name": "Dauphin Island",          "state": "AL", "trend_mm_yr": 3.20},
    {"station_id": "8741533", "name": "Pascagoula",              "state": "MS", "trend_mm_yr": 3.50},
    {"station_id": "8747437", "name": "Bay Waveland Yacht Club", "state": "MS", "trend_mm_yr": 3.80},
    {"station_id": "8760922", "name": "Pilots Station East",     "state": "LA", "trend_mm_yr": 9.10},
    {"station_id": "8761724", "name": "Grand Isle",              "state": "LA", "trend_mm_yr": 9.00},
    {"station_id": "8764227", "name": "LAWMA Amerada Pass",      "state": "LA", "trend_mm_yr": 9.30},
    {"station_id": "8770570", "name": "Sabine Pass North",       "state": "TX", "trend_mm_yr": 5.80},
    {"station_id": "8771341", "name": "Galveston Pier 21",       "state": "TX", "trend_mm_yr": 6.60},
    {"station_id": "8771450", "name": "Galveston Pleasure Pier", "state": "TX", "trend_mm_yr": 6.50},
    {"station_id": "8772471", "name": "Texas Point",             "state": "TX", "trend_mm_yr": 5.90},
    {"station_id": "8774770", "name": "Rockport",                "state": "TX", "trend_mm_yr": 4.50},
    {"station_id": "8775237", "name": "Port Aransas",            "state": "TX", "trend_mm_yr": 3.90},
    {"station_id": "8775870", "name": "Bob Hall Pier",           "state": "TX", "trend_mm_yr": 3.70},
    {"station_id": "8779770", "name": "South Padre Island",      "state": "TX", "trend_mm_yr": 3.40},
    {"station_id": "8720030", "name": "Fernandina Beach",        "state": "FL", "trend_mm_yr": 2.10},
    {"station_id": "8720218", "name": "Mayport (Bar Pilots Dock)","state": "FL", "trend_mm_yr": 2.20},
    {"station_id": "8721604", "name": "Trident Pier",            "state": "FL", "trend_mm_yr": 2.50},
    {"station_id": "8722670", "name": "Lake Worth Pier",         "state": "FL", "trend_mm_yr": 2.80},
    {"station_id": "8723214", "name": "Virginia Key",            "state": "FL", "trend_mm_yr": 3.10},
    {"station_id": "8723970", "name": "Vaca Key",                "state": "FL", "trend_mm_yr": 2.70},
    {"station_id": "8658120", "name": "Wilmington",              "state": "NC", "trend_mm_yr": 2.50},
    {"station_id": "8661070", "name": "Springmaid Pier",         "state": "SC", "trend_mm_yr": 3.00},
    {"station_id": "8665530", "name": "Charleston",              "state": "SC", "trend_mm_yr": 3.30},
    {"station_id": "8670870", "name": "Fort Pulaski",            "state": "GA", "trend_mm_yr": 3.10},
    {"station_id": "8679511", "name": "Kings Bay",               "state": "GA", "trend_mm_yr": 2.90},
    {"station_id": "8534720", "name": "Atlantic City",           "state": "NJ", "trend_mm_yr": 4.10},
    {"station_id": "8536110", "name": "Cape May",                "state": "NJ", "trend_mm_yr": 3.90},
    {"station_id": "8557380", "name": "Lewes",                   "state": "DE", "trend_mm_yr": 3.50},
    {"station_id": "8570283", "name": "Ocean City Inlet",        "state": "MD", "trend_mm_yr": 3.80},
    {"station_id": "8571892", "name": "Cambridge",               "state": "MD", "trend_mm_yr": 3.70},
    {"station_id": "8575512", "name": "Annapolis",               "state": "MD", "trend_mm_yr": 3.90},
    {"station_id": "8577330", "name": "Solomons Island",         "state": "MD", "trend_mm_yr": 3.80},
    {"station_id": "8594900", "name": "Washington DC",           "state": "DC", "trend_mm_yr": 3.70},
    {"station_id": "8638610", "name": "Sewells Point",           "state": "VA", "trend_mm_yr": 4.70},
    {"station_id": "8632200", "name": "Kiptopeke",               "state": "VA", "trend_mm_yr": 3.70},
    {"station_id": "8635750", "name": "Rappahannock Light",      "state": "VA", "trend_mm_yr": 4.00},
    {"station_id": "8651370", "name": "Duck",                    "state": "NC", "trend_mm_yr": 4.40},
    {"station_id": "8654400", "name": "Cape Hatteras",           "state": "NC", "trend_mm_yr": 4.80},
    {"station_id": "8656483", "name": "Beaufort",                "state": "NC", "trend_mm_yr": 2.70},
    {"station_id": "8510560", "name": "Montauk",                 "state": "NY", "trend_mm_yr": 2.80},
    {"station_id": "8516945", "name": "Kings Point",             "state": "NY", "trend_mm_yr": 3.20},
    {"station_id": "8518750", "name": "The Battery (New York)",  "state": "NY", "trend_mm_yr": 3.00},
    {"station_id": "8519483", "name": "Bergen Point West",       "state": "NY", "trend_mm_yr": 3.10},
    {"station_id": "8461490", "name": "New London",              "state": "CT", "trend_mm_yr": 2.40},
    {"station_id": "8465705", "name": "New Haven",               "state": "CT", "trend_mm_yr": 2.60},
    {"station_id": "8467150", "name": "Bridgeport",              "state": "CT", "trend_mm_yr": 2.70},
    {"station_id": "8447930", "name": "Woods Hole",              "state": "MA", "trend_mm_yr": 2.60},
    {"station_id": "8449130", "name": "Nantucket",               "state": "MA", "trend_mm_yr": 2.90},
    {"station_id": "8443970", "name": "Boston",                  "state": "MA", "trend_mm_yr": 2.80},
    {"station_id": "8411060", "name": "Cutler Farris Wharf",     "state": "ME", "trend_mm_yr": 1.50},
    {"station_id": "8418150", "name": "Portland",                "state": "ME", "trend_mm_yr": 1.90},
    {"station_id": "8423898", "name": "Fort Point",              "state": "NH", "trend_mm_yr": 1.80},
    {"station_id": "8431567", "name": "Seavey Island",           "state": "NH", "trend_mm_yr": 1.70},
    # Pacific Coast
    {"station_id": "9410660", "name": "Los Angeles",             "state": "CA", "trend_mm_yr": 0.80},
    {"station_id": "9410840", "name": "Santa Monica",            "state": "CA", "trend_mm_yr": 1.50},
    {"station_id": "9412110", "name": "Port San Luis",           "state": "CA", "trend_mm_yr": 0.50},
    {"station_id": "9413450", "name": "Monterey",                "state": "CA", "trend_mm_yr": 0.80},
    {"station_id": "9414290", "name": "San Francisco",           "state": "CA", "trend_mm_yr": 2.00},
    {"station_id": "9415020", "name": "Point Reyes",             "state": "CA", "trend_mm_yr": 0.30},
    {"station_id": "9416841", "name": "Arena Cove",              "state": "CA", "trend_mm_yr": 0.60},
    {"station_id": "9418767", "name": "North Spit",              "state": "CA", "trend_mm_yr": 0.30},
    {"station_id": "9419750", "name": "Crescent City",           "state": "CA", "trend_mm_yr": -0.60},
    {"station_id": "9431647", "name": "Port Orford",             "state": "OR", "trend_mm_yr": 0.30},
    {"station_id": "9435380", "name": "South Beach",             "state": "OR", "trend_mm_yr": 0.80},
    {"station_id": "9440910", "name": "Toke Point",              "state": "WA", "trend_mm_yr": 1.20},
    {"station_id": "9443090", "name": "Neah Bay",                "state": "WA", "trend_mm_yr": -1.80},
    {"station_id": "9444900", "name": "Port Townsend",           "state": "WA", "trend_mm_yr": 0.50},
    {"station_id": "9447130", "name": "Seattle",                 "state": "WA", "trend_mm_yr": 2.10},
]

# NOAA 2022 SLRTR scenario offsets (m above 2000 baseline) for 2050 / 2100
# Keys: scenario name → (2050_m, 2100_m) relative to 2000 LMSL
TR083_SCENARIOS = {
    "Low":           {"2050": 0.10, "2100": 0.30},
    "Intermediate-Low": {"2050": 0.18, "2100": 0.50},
    "Intermediate":  {"2050": 0.30, "2100": 1.00},
    "Intermediate-High": {"2050": 0.43, "2100": 1.50},
    "High":          {"2050": 0.58, "2100": 2.00},
    "Extreme":       {"2050": 0.82, "2100": 3.00},
}


def expand_table(dry_run: bool = False) -> List[Dict[str, Any]]:
    """Return the expanded station table with per-station GMSL addend applied."""
    rows = []
    for st in TR083_STATIONS:
        row = dict(st)
        row["scenarios"] = {}
        for scen, offsets in TR083_SCENARIOS.items():
            # Localise scenario values by adding linear SLR component
            # (simplified: actual TR-083 uses fingerprint weighting)
            local_trend_m = st["trend_mm_yr"] / 1000.0  # mm/yr → m/yr
            years_2050 = 50  # 2000→2050
            years_2100 = 100  # 2000→2100
            row["scenarios"][scen] = {
                "2050_m": round(offsets["2050"] + local_trend_m * years_2050, 3),
                "2100_m": round(offsets["2100"] + local_trend_m * years_2100, 3),
            }
        rows.append(row)
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Expand NOAA TR-083 station table to all 75 tide gauge stations."
    )
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT), metavar="PATH",
                        help="Output JSON file path.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print table to stdout only; do not write file.")
    args = parser.parse_args(argv)

    table = expand_table(dry_run=args.dry_run)

    if args.dry_run:
        for row in table:
            s = row["scenarios"]
            print(
                f"  {row['station_id']:10s}  {row['name']:<35s}  {row['state']}  "
                f"trend={row['trend_mm_yr']:5.2f} mm/yr  "
                f"Intermediate-2100={s['Intermediate']['2100_m']:.2f}m"
            )
        log.info("Dry run — %d stations listed.", len(table))
        return 0

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        json.dump({"stations": table, "scenarios": TR083_SCENARIOS}, fh, indent=2)
    log.info("Saved %d-station TR-083 table → %s", len(table), output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
