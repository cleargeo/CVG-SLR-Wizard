#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# CVG SLR Wizard — run_tests.py
# =============================================================================
"""
Convenience script to run the SLR Wizard test suite from the project root.

Usage:
    python run_tests.py           # unit tests only (fast)
    python run_tests.py --all     # all tests including integration
    python run_tests.py --cov     # with coverage report
"""

import subprocess
import sys


def main():
    args = sys.argv[1:]
    run_all = "--all" in args
    run_cov = "--cov" in args

    cmd = ["pytest", "tests/", "-v", "--tb=short"]

    if not run_all:
        cmd += ["-m", "not integration and not slow"]

    if run_cov:
        cmd += [
            "--cov=slr_wizard",
            "--cov-report=html",
            "--cov-report=term-missing",
        ]

    print(f"\n  CVG SLR Wizard — Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
