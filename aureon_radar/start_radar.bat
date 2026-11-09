@echo off
REM Thin wrapper. The canonical entry is python -m aureon.launch.master.
REM This file does not copy .env and does not arm live trading.
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
python -m aureon.launch.live_gate
if errorlevel 1 (
  set "AUREON_LIVE_TRADING=0"
  set "AUREON_AUTONOMY_MODE=guarded"
  set "AUREON_DISABLE_REAL_ORDERS=1"
)
python -m aureon.launch.master %*
exit /b %ERRORLEVEL%
