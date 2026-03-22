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
"""batch_report_gen.py — Generate PDF reports for multiple existing SLR output JSON files.

Scans a directory for ``*.json`` result files produced by the SLR Wizard API or CLI
and regenerates a PDF report for each one.  Useful for re-styling reports after a
template update or bulk-regenerating a deliverable set.

Usage::

    python tools/batch_report_gen.py --input-dir ./results --output-dir ./pdfs
    python tools/batch_report_gen.py results/slr_output.json --output-dir ./pdfs
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _generate_pdf(result: dict, output_path: Path) -> bool:
    """Invoke the SLR Wizard report module to render *result* → PDF."""
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from slr_wizard.report import SLRPDFReport

        rpt = SLRPDFReport(result)
        rpt.render(str(output_path))
        return True
    except Exception as exc:
        log.error("Failed to generate PDF for %s: %s", output_path.name, exc)
        return False


def process_file(json_path: Path, output_dir: Path) -> bool:
    """Generate a PDF for a single JSON result file."""
    try:
        result = _load_json(json_path)
    except Exception as exc:
        log.error("Cannot read %s: %s", json_path, exc)
        return False

    pdf_name = json_path.stem + ".pdf"
    pdf_path = output_dir / pdf_name

    log.info("Generating PDF: %s → %s", json_path.name, pdf_path)
    success = _generate_pdf(result, pdf_path)
    if success:
        log.info("  %s  Saved: %s", "\u2705", pdf_path)
    else:
        log.warning("  %s  Failed: %s", "\u274c", pdf_path)
    return success


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch-generate SLR Wizard PDF reports from existing JSON result files."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input-dir", metavar="DIR",
                       help="Directory to scan for *.json result files.")
    group.add_argument("json_files", nargs="*", metavar="JSON",
                       help="One or more explicit JSON file paths.")
    parser.add_argument("--output-dir", default=".", metavar="DIR",
                        help="Directory to write PDF reports (default: current dir).")
    parser.add_argument("--recursive", action="store_true",
                        help="Recurse into subdirectories when using --input-dir.")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect input files
    if args.input_dir:
        base = Path(args.input_dir)
        pattern = "**/*.json" if args.recursive else "*.json"
        files = sorted(base.glob(pattern))
    else:
        files = [Path(f) for f in args.json_files]

    if not files:
        log.error("No JSON files found.")
        return 1

    log.info("Processing %d JSON file(s)...", len(files))
    results = [process_file(f, output_dir) for f in files]

    passed = sum(results)
    failed = len(results) - passed
    log.info("\nDone: %d generated, %d failed.", passed, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
