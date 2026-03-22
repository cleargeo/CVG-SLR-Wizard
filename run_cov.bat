@echo off
:: =============================================================================
:: (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
:: CVG SLR Wizard — Run Tests with Coverage (Windows)
:: =============================================================================
title CVG SLR Wizard — Coverage

echo.
echo  Running CVG SLR Wizard Tests with Coverage...
echo.

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

pytest tests\ --cov=slr_wizard --cov-report=html --cov-report=term-missing -v

echo.
echo  Coverage report saved to: htmlcov\index.html
echo.
pause
