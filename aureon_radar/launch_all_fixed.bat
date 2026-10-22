@echo off
REM ============================================================
REM AUREON RADAR LAUNCHER — All Compartments
REM Fixed 2026-09-04: UTF-8 encoding, proper env loading
REM ============================================================

setlocal

REM Set Python encoding to UTF-8 (prevents cp1252 Unicode errors)
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

REM Change to radar directory
cd /d "C:\Users\user\.kimi_openclaw\workspace\aureon_radar"

echo ============================================================
echo  AUREON PHI-RADAR — LAUNCHING ALL COMPARTMENTS
echo ============================================================
echo.

REM Kill any existing radar processes first
echo [1/7] Cleaning up old processes...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM Launch compartments in background (hidden windows)
echo [2/7] Starting Planetary Switchboard...
start /B /MIN "" "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe" -u planetary_switchboard.py > planetary_meta.log 2>&1

echo [3/7] Starting Ollama Switchboard...
start /B /MIN "" "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe" -u ollama_switchboard.py > ollama_switchboard.log 2>&1

echo [4/7] Starting Alpaca Switchboard...
start /B /MIN "" "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe" -u alpaca_switchboard.py > stock_meta.log 2>&1

echo [5/7] Starting Binance Switchboard...
start /B /MIN "" "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe" -u binance_switchboard.py > correlation_meta.log 2>&1

echo [6/7] Starting Aureon OS Bridge...
start /B /MIN "" "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe" -u aureon_bridge.py > aureon_bridge.log 2>&1

echo [7/7] Starting Main Radar...
start /B /MIN "" "C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe" -u aureon_phi_radar.py > radar.log 2>&1

echo.
echo ============================================================
echo  ALL COMPARTMENTS LAUNCHED
echo ============================================================
echo.
echo Check these files for live status:
echo   - radar.log
echo   - planetary_meta.log
echo   - ollama_switchboard.log
echo   - stock_meta.log
echo   - correlation_meta.log
echo   - aureon_bridge.log
echo.
pause
