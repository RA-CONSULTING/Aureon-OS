@echo off
REM Thin wrapper. The canonical entry is python -m aureon.launch.master.
REM This file does not copy .env and does not arm live trading.
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
python -m aureon.launch.master %*
exit /b %ERRORLEVEL%
