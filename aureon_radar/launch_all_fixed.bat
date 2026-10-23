@echo off
REM Thin wrapper. The canonical entry is python -m aureon.launch.master.
REM This file does not arm live trading.
setlocal
set "PYTHONIOENCODING=utf-8"
set "PYTHONUNBUFFERED=1"
set "ROOT=%~dp0.."
cd /d "%ROOT%"
python -m aureon.launch.master %*
exit /b %ERRORLEVEL%
