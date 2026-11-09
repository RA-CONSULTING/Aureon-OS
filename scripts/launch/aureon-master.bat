@echo off
REM Canonical Aureon launcher for Windows.
REM Live mode stays locked unless the stage 11 gate reports clear and AUREON_OPERATOR_ALLOW_LIVE is set.
setlocal
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"
python -m aureon.launch.live_gate
if errorlevel 1 (
  set "AUREON_LIVE_TRADING=0"
  set "AUREON_AUTONOMY_MODE=guarded"
  set "AUREON_DISABLE_REAL_ORDERS=1"
)
python -m aureon.launch.master %*
exit /b %ERRORLEVEL%
