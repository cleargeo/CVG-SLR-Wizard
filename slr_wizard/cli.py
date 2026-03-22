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
cli.py — Command-line interface for the CVG SLR Wizard.

Usage:
  slr-wizard run   --config config.json [--resume]
  slr-wizard batch --config config.json
  slr-wizard web   [--host 0.0.0.0] [--port 8000]
  slr-wizard insights [QUERY]
  slr-wizard stations
  slr-wizard new-config [--output config.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    # Ensure Unicode characters print correctly on Windows cp1252 terminals.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.verbose if hasattr(args, "verbose") else False)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def _cmd_run(args) -> int:
    """Run a single SLR inundation analysis."""
    from .config import load_config, validate_config
    from .processing import run_inundation
    from .report import write_reports

    cfg = load_config(args.config)

    # ── CLI overrides for projection scenario and planning horizon ────────────
    if getattr(args, "scenario", None):
        from .config import resolve_scenario
        try:
            cfg.projection.scenario = resolve_scenario(args.scenario)
        except ValueError as e:
            print(f"[ERROR] --scenario: {e}", file=sys.stderr)
            return 1

    if getattr(args, "year", None) is not None:
        cfg.projection.target_year = int(args.year)

    if getattr(args, "scenario", None) or getattr(args, "year", None):
        print(
            f"  [CLI override] scenario={cfg.projection.scenario}  "
            f"year={cfg.projection.target_year}"
        )

    try:
        validate_config(cfg)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    result = run_inundation(cfg, resume=args.resume)

    out_paths = write_reports(result, cfg, cfg.output.output_dir)
    _print_result_summary(result, out_paths)
    return 0


def _cmd_batch(args) -> int:
    """Run all scenario × year combinations."""
    from .config import load_config, validate_config
    from .processing import run_batch
    from .report import write_reports

    cfg = load_config(args.config)
    try:
        validate_config(cfg)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    cfg.processing.run_all_scenarios = True
    results = run_batch(cfg)
    print(f"\n✓ Batch complete — {len(results)} run(s) finished.")
    for r in results:
        print(f"  {r.scenario:18s} {r.target_year}  →  {r.inundated_pct:.1f}% inundated  max={r.max_depth_ft:.2f} ft")
    return 0


def _cmd_web(args) -> int:
    """Start the web UI / API server."""
    try:
        import uvicorn
        from .web_api import create_app
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except ImportError:
        print("[ERROR] uvicorn is required: pip install uvicorn", file=sys.stderr)
        return 1
    return 0


def _cmd_insights(args) -> int:
    """Search the SLR knowledge base."""
    from .insights import search_insights, list_topics
    query = " ".join(args.query) if args.query else ""
    if not query:
        print("Available knowledge base topics:")
        for t in list_topics():
            print(f"  • {t}")
        return 0
    results = search_insights(query)
    if not results:
        print(f"No results found for: {query!r}")
        return 0
    for entry in results:
        print(f"\n{'='*60}")
        print(f"  [{entry.topic}] {entry.title}")
        print(f"  Source: {entry.source}")
        print(f"{'─'*60}")
        print(entry.body)
    return 0


def _cmd_stations(args) -> int:
    """List stations with embedded SLR data."""
    from .noaa import list_supported_stations
    stations = list_supported_stations()
    print(f"\n{'ID':12s} {'Name':25s} {'State':6s} {'Lat':8s} {'Lon':10s}")
    print("─" * 65)
    for s in stations:
        print(f"{s.station_id:12s} {s.name:25s} {s.state:6s} {s.lat:8.4f} {s.lon:10.4f}")
    return 0


def _cmd_new_config(args) -> int:
    """Write a default inundation config file to disk."""
    from .config import SLRInundationConfig, save_config
    cfg = SLRInundationConfig()
    out = Path(args.output or "slr_config.json")
    save_config(cfg, out)
    print(f"Default inundation config written → {out}")
    print(f"  Edit inputs.dem_path and inputs.noaa_station_id before running.")
    return 0


def _cmd_project_slr(args) -> int:
    """Quick SLR projection lookup (no DEM required).

    Examples
    --------
    # All 6 scenarios for Key West, planning horizon 2070:
      slr-wizard project --station 8724580 --year 2070

    # Single scenario (intermediate_high) for default station at 2050:
      slr-wizard project --year 2050 --scenario intermediate_high
    """
    from .noaa import get_all_scenarios_for_year, get_slr_projection

    year = args.year
    station = args.station or None
    scenario = getattr(args, "scenario", None) or None

    if scenario and scenario.lower() != "all":
        # ── Single-scenario output ────────────────────────────────────────────
        from .config import resolve_scenario
        try:
            canonical = resolve_scenario(scenario)
        except ValueError as e:
            print(f"[ERROR] --scenario: {e}", file=sys.stderr)
            return 1
        ft = get_slr_projection(canonical, year, station)
        m = ft / 3.28084
        print(
            f"\nNOAA TR-083 SLR  station={station or 'national_avg'}"
            f"  scenario={canonical}  year={year}\n"
            f"  {ft:.3f} ft  ({m:.3f} m)\n"
        )
    else:
        # ── All 6 scenarios ───────────────────────────────────────────────────
        print(
            f"\nNOAA TR-083 SLR Projections  station={station or 'national_avg'}"
            f"  year={year}\n"
        )
        print(f"{'Scenario':22s}  {'ft':>8s}  {'m':>8s}")
        print("─" * 44)
        scenarios = get_all_scenarios_for_year(year, station_id=station)
        for sc, ft in scenarios.items():
            m = ft / 3.28084
            print(f"{sc:22s}  {ft:8.3f}  {m:8.3f}")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slr-wizard",
        description="CVG SLR Wizard — Sea Level Rise Inundation Grid Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "© Clearview Geographic LLC  |  azelenski@clearviewgeographic.com\n"
            "https://www.clearviewgeographic.com"
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(title="commands", dest="command")

    # run
    p_run = sub.add_parser("run", help="Run SLR inundation analysis")
    p_run.add_argument("--config", required=True, help="Path to JSON config file")
    p_run.add_argument("--resume", action="store_true", default=True, help="Resume from checkpoint")
    p_run.add_argument(
        "--scenario", default=None,
        metavar="SCENARIO",
        help=(
            "Override the SLR projection scenario from the config file. "
            "Choices: low | intermediate_low | intermediate | intermediate_high | high | extreme "
            "(aliases: l, il, i, ih, h, e)."
        ),
    )
    p_run.add_argument(
        "--year", type=int, default=None,
        metavar="YEAR",
        help=(
            "Override the planning horizon year from the config file "
            "(e.g. 2050, 2070, 2100).  Valid range: 2020–2100."
        ),
    )
    p_run.set_defaults(func=_cmd_run)

    # batch
    p_batch = sub.add_parser("batch", help="Run all scenario/year combinations")
    p_batch.add_argument("--config", required=True, help="Path to JSON config file")
    p_batch.set_defaults(func=_cmd_batch)

    # web
    p_web = sub.add_parser("web", help="Start web UI")
    p_web.add_argument("--host", default="127.0.0.1", help="Bind host")
    p_web.add_argument("--port", type=int, default=8010, help="Port (default 8010)")
    p_web.set_defaults(func=_cmd_web)

    # insights
    p_ins = sub.add_parser("insights", help="Search knowledge base")
    p_ins.add_argument("query", nargs="*", help="Search query")
    p_ins.set_defaults(func=_cmd_insights)

    # stations
    p_st = sub.add_parser("stations", help="List supported NOAA CO-OPS stations")
    p_st.set_defaults(func=_cmd_stations)

    # new-config
    p_cfg = sub.add_parser("new-config", help="Generate a default config file")
    p_cfg.add_argument("--output", default="slr_config.json", help="Output path")
    p_cfg.set_defaults(func=_cmd_new_config)

    # project
    p_proj = sub.add_parser(
        "project",
        help="Quick SLR projection lookup (no DEM required)",
        description=(
            "Look up NOAA TR-083 relative sea level rise for a given planning horizon.\n"
            "When --scenario is omitted all 6 scenarios are shown side-by-side.\n\n"
            "Examples:\n"
            "  slr-wizard project --station 8724580 --year 2070\n"
            "  slr-wizard project --station 8724580 --year 2050 --scenario intermediate_high\n"
            "  slr-wizard project --year 2100 --scenario ih"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_proj.add_argument(
        "--year", type=int, default=2070,
        metavar="YEAR",
        help="Planning horizon year, e.g. 2050, 2070, 2100 (default: 2070).",
    )
    p_proj.add_argument(
        "--station", default=None,
        metavar="STATION_ID",
        help="NOAA CO-OPS station ID (e.g. 8724580 for Key West, FL). "
             "Falls back to national-average table when omitted.",
    )
    p_proj.add_argument(
        "--scenario", default=None,
        metavar="SCENARIO",
        help=(
            "SLR projection scenario.  When omitted all 6 scenarios are shown.\n"
            "Choices: low | intermediate_low | intermediate | intermediate_high | high | extreme\n"
            "Aliases: l  | il              | i            | ih               | h    | e"
        ),
    )
    p_proj.set_defaults(func=_cmd_project_slr)

    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _print_result_summary(result, out_paths: dict) -> None:
    print(f"\n{'═'*55}")
    print(f"  CVG SLR Wizard — Run Complete")
    print(f"{'═'*55}")
    print(f"  Run ID    : {result.run_id}")
    print(f"  Scenario  : {result.scenario}")
    print(f"  Year      : {result.target_year}")
    print(f"  SLR offset: {result.slr_offset_ft:.3f} ft")
    print(f"  WSE NAVD88: {result.water_surface_navd88_ft:.3f} ft")
    print(f"  Inundated : {result.inundated_pct:.1f}%  ({result.inundated_cells:,} cells)")
    print(f"  Max depth : {result.max_depth_ft:.2f} ft")
    print(f"  Elapsed   : {result.elapsed_sec:.1f} s")
    if out_paths:
        print(f"\n  Reports:")
        for fmt, path in out_paths.items():
            print(f"    [{fmt.upper()}] {path}")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    sys.exit(main())
