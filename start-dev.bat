@echo off
:: =============================================================================
:: (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
:: CVG SLR Wizard — Development Server Launcher (Windows)
:: Author: Alex Zelenski, GISP | azelenski@clearviewgeographic.com
:: =============================================================================
title CVG SLR Wizard — Dev Server

echo.
echo  ================================================================
echo    CVG SLR Wizard — Starting Development Server
echo    Port: 8010  ^|  http://localhost:8010
echo    Swagger UI: http://localhost:8010/docs
echo  ================================================================
echo.

:: Check for virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo  [INFO] Virtual environment activated.
) else (
    echo  [WARN] No .venv found — using system Python.
)

:: Install if needed
pip show slr-wizard >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Installing slr-wizard...
    pip install -e ".[web]" -q
)

echo  [INFO] Launching slr-wizard web server...
echo.

slr-wizard web --host 127.0.0.1 --port 8010

echo.
echo  [INFO] Server stopped.
pause
