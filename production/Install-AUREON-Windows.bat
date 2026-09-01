@echo off
setlocal
set "AUREON_REPO=%~dp0.."
set "AUREON_PYTHON=%AUREON_REPO%\.venv\Scripts\python.exe"
set "AUREON_BOOTSTRAP=%AUREON_REPO%\scripts\bootstrap\protected_bootstrap_v05.py"
if not exist "%AUREON_PYTHON%" (
  echo Aureon protected installer boundary is unavailable; refusing installation. 1>&2
  exit /b 1
)
if not exist "%AUREON_BOOTSTRAP%" (
  echo Aureon protected installer boundary is unavailable; refusing installation. 1>&2
  exit /b 1
)
echo Aureon installation and release are on terminal protection HOLD. 1>&2
"%AUREON_PYTHON%" -I -S -B "%AUREON_BOOTSTRAP%" --target-id production-supervisor
exit /b %ERRORLEVEL%
