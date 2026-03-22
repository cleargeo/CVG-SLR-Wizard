@echo off
:: =============================================================================
:: (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
:: CVG SLR Wizard — Run Tests (Windows)
:: =============================================================================
title CVG SLR Wizard — Tests

echo.
echo  Running CVG SLR Wizard Test Suite...
echo.

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

:: NOTE: Use explicit test file paths to prevent pytest from resolving
:: rootdir to the sibling CVG_Storm Surge Wizard directory and running
:: SSW's test suite instead of the SLR Wizard's own tests.
pytest ^
    tests\test_slr_wizard.py ^
    tests\test_config.py ^
    tests\test_noaa.py ^
    tests\test_processing.py ^
    tests\test_insights.py ^
    -v --tb=short ^
    -m "not integration and not slow" ^
    --override-ini="addopts=" ^
    --override-ini="testpaths="

echo.
echo  Done.
pause
