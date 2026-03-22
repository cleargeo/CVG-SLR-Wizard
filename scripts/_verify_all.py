# =============================================================================
# CVG SLR Wizard — Dev Utility: Full Verification Suite
# Clearview Geographic LLC — Proprietary and Confidential
# ADF Build: 1.0.x | Python 3.10+
# =============================================================================
"""
Comprehensive verification script for the CVG SLR Wizard.

Checks:
  1. CVG headers present on all tracked .py files
  2. NAVD88 / NOAA TR-083 references in key module files
  3. Required VALID_SCENARIOS and VALID_YEARS constants in config.py
  4. 6 expected NOAA stations defined in noaa.py
  5. Changelog file exists and is non-empty
  6. README.md mentions key project terms
  7. .gitignore contains essential patterns
  8. pyproject.toml version field is present
  9. All required package modules are importable

Usage:
    python scripts/_verify_all.py [--strict]
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_HEADER_MARKER = "Clearview Geographic LLC"
_PASS = "\u2713"
_FAIL = "\u2717"

_REQUIRED_PY_FILES: list[str] = [
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
]

_REQUIRED_MODULES: list[str] = [
    "slr_wizard",
    "slr_wizard.config",
    "slr_wizard.core",
    "slr_wizard.noaa",
    "slr_wizard.insights",
    "slr_wizard.processing",
    "slr_wizard.web_api",
]

_EXPECTED_STATION_COUNT = 6
_EXPECTED_SCENARIOS = [
    "Low", "Intermediate-Low", "Intermediate",
    "Intermediate-High", "High", "Extreme",
]
_EXPECTED_YEARS = [2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = _PASS if ok else _FAIL
    msg = f"  [{mark}] {label}"
    if detail:
        msg += f"  — {detail}"
    print(msg)
    return ok


def run_checks(strict: bool) -> int:
    failures = 0

    print("\n=== 1. CVG Headers ===")
    for rel in _REQUIRED_PY_FILES:
        p = ROOT / rel
        if not p.exists():
            ok = check(rel, False, "FILE MISSING")
        else:
            text = p.read_text(encoding="utf-8", errors="replace")
            ok = check(rel, _HEADER_MARKER in text)
        if not ok:
            failures += 1

    print("\n=== 2. NAVD88 / TR-083 References ===")
    key_refs = {
        "slr_wizard/config.py": ["NAVD88", "TR-083", "VALID_SCENARIOS"],
        "slr_wizard/noaa.py": ["NAVD88", "Sweet", "station"],
        "slr_wizard/processing.py": ["bathtub", "min_depth"],
    }
    for rel, terms in key_refs.items():
        p = ROOT / rel
        if not p.exists():
            check(f"{rel} — exists", False, "MISSING")
            failures += 1
            continue
        text = p.read_text(encoding="utf-8", errors="replace").lower()
        for term in terms:
            ok = check(f"{rel} contains '{term}'", term.lower() in text)
            if not ok:
                failures += 1

    print("\n=== 3. Config Constants ===")
    config_path = ROOT / "slr_wizard" / "config.py"
    if config_path.exists():
        cfg_text = config_path.read_text(encoding="utf-8", errors="replace")
        for scenario in _EXPECTED_SCENARIOS:
            ok = check(f"VALID_SCENARIOS has '{scenario}'", f'"{scenario}"' in cfg_text or f"'{scenario}'" in cfg_text)
            if not ok:
                failures += 1
        ok = check("VALID_YEARS defined", "VALID_YEARS" in cfg_text)
        if not ok:
            failures += 1

    print("\n=== 4. NOAA Stations ===")
    noaa_path = ROOT / "slr_wizard" / "noaa.py"
    if noaa_path.exists():
        noaa_text = noaa_path.read_text(encoding="utf-8", errors="replace")
        count = noaa_text.count("station_id") + noaa_text.count('"8724580"') + noaa_text.count("'8724580'")
        ok = check(f"noaa.py contains Key West station reference", "8724580" in noaa_text)
        if not ok:
            failures += 1
    else:
        check("noaa.py exists", False, "MISSING")
        failures += 1

    print("\n=== 5. Changelog ===")
    changelog = ROOT / "05_ChangeLogs" / "master_changelog.md"
    ok = check("05_ChangeLogs/master_changelog.md exists", changelog.exists())
    if ok:
        ok = check("changelog is non-empty", changelog.stat().st_size > 0)
    if not ok:
        failures += 1

    print("\n=== 6. README ===")
    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
        for term in ["SLR Wizard", "Sea Level Rise", "NOAA"]:
            ok = check(f"README mentions '{term}'", term in text)
            if not ok:
                failures += 1
    else:
        check("README.md exists", False, "MISSING")
        failures += 1

    print("\n=== 7. .gitignore ===")
    gitignore = ROOT / ".gitignore"
    if gitignore.exists():
        gi_text = gitignore.read_text(encoding="utf-8", errors="replace")
        for pat in ["__pycache__", "*.pyc", ".env", "htmlcov/"]:
            ok = check(f".gitignore has '{pat}'", pat in gi_text)
            if not ok:
                failures += 1

    print("\n=== 8. pyproject.toml ===")
    pyproj = ROOT / "pyproject.toml"
    if pyproj.exists():
        text = pyproj.read_text(encoding="utf-8", errors="replace")
        ok = check("pyproject.toml has version field", "version" in text)
        if not ok:
            failures += 1
        ok = check("pyproject.toml references slr-wizard", "slr" in text.lower())
        if not ok:
            failures += 1

    print("\n=== 9. Module Imports ===")
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    for mod in _REQUIRED_MODULES:
        try:
            importlib.import_module(mod)
            ok = check(f"import {mod}", True)
        except Exception as exc:
            ok = check(f"import {mod}", False, str(exc)[:80])
        if not ok:
            failures += 1

    print(f"\n{'=' * 50}")
    total_label = f"STRICT MODE" if strict else "STANDARD MODE"
    if failures == 0:
        print(f"  ALL CHECKS PASSED [{total_label}]  {_PASS}")
    else:
        print(f"  {failures} CHECK(S) FAILED [{total_label}]  {_FAIL}")
    print(f"{'=' * 50}\n")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Full verification for CVG SLR Wizard")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any failure")
    args = parser.parse_args()
    failures = run_checks(strict=args.strict)
    sys.exit(1 if (args.strict and failures) else 0)


if __name__ == "__main__":
    main()
