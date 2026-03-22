# =============================================================================
# CVG SLR Wizard — Dev Utility: Add CVG Headers to Source Files
# Clearview Geographic LLC — Proprietary and Confidential
# ADF Build: 1.0.x | Python 3.10+
# =============================================================================
"""
Targeted header injector for the CVG SLR Wizard Python source files.

Adds the standard CVG ADF proprietary header block to each file that
is missing it. Preserves existing shebangs (#!/usr/bin/env python3) at
the top of the file.

Usage:
    python scripts/_add_cvg_headers.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Ordered manifest of files that must carry the CVG header
_MANIFEST: list[str] = [
    "slr_wizard/__init__.py",
    "slr_wizard/cli.py",
    "slr_wizard/config.py",
    "slr_wizard/core.py",
    "slr_wizard/insights.py",
    "slr_wizard/io.py",
    "slr_wizard/monitoring.py",
    "slr_wizard/noaa.py",
    "slr_wizard/paths.py",
    "slr_wizard/processing.py",
    "slr_wizard/recovery.py",
    "slr_wizard/report.py",
    "slr_wizard/vdatum.py",
    "slr_wizard/web_api.py",
    "slr_wizard/web.py",
    "tests/conftest.py",
    "tests/test_config.py",
    "tests/test_insights.py",
    "tests/test_noaa.py",
    "tests/test_processing.py",
    "tests/test_slr_wizard.py",
    "scripts/run_slr.py",
    "portal/app.py",
]

_HEADER_MARKER = "Clearview Geographic LLC"

_HEADER_TEMPLATE = """\
# =============================================================================
# CVG SLR Wizard — {title}
# Clearview Geographic LLC — Proprietary and Confidential
# ADF Build: 1.0.x | Python 3.10+
# =============================================================================
"""


def _needs_header(text: str) -> bool:
    return _HEADER_MARKER not in text


def _inject(path: Path, dry_run: bool) -> bool:
    """Inject header into *path*. Returns True if modified."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not _needs_header(text):
        return False

    title = path.stem.replace("_", " ").title()
    header = _HEADER_TEMPLATE.format(title=title)

    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("#!"):
        shebang = lines[0]
        rest = "".join(lines[1:])
        new_text = shebang + header + rest
    else:
        new_text = header + text

    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Add CVG headers to SLR Wizard source files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = parser.parse_args()

    modified = 0
    missing  = 0
    for rel in _MANIFEST:
        p = ROOT / rel
        if not p.exists():
            print(f"  MISSING  {rel}")
            missing += 1
            continue
        changed = _inject(p, dry_run=args.dry_run)
        tag = "DRY-RUN" if args.dry_run and changed else ("ADDED  " if changed else "OK     ")
        print(f"  {tag}  {rel}")
        if changed:
            modified += 1

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Headers added: {modified}  |  Missing files: {missing}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
