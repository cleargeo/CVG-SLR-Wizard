@echo off
:: =============================================================================
:: CVG SLR Wizard — Production Direct Start (no Docker)
:: Use this when Docker Desktop is not available.
:: Pairs with cloudflared tunnel for public HTTPS access.
::
:: App runs at: http://localhost:8010
:: Public URL:  https://slr.cleargeo.tech  (via cloudflare tunnel)
:: =============================================================================
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [CVG SLRW] Starting SLR Wizard API (production, direct)...
echo [CVG SLRW] API:    http://localhost:8010
echo [CVG SLRW] Docs:   http://localhost:8010/docs
echo [CVG SLRW] Health: http://localhost:8010/health
echo.

:: Optional: restrict allowed data paths
set SLRW_ALLOWED_DATA_ROOTS=G:\2019;Z:\2019

python -m uvicorn slr_wizard.web_api:app ^
    --host 0.0.0.0 ^
    --port 8010 ^
    --workers 2 ^
    --log-level info ^
    --access-log
