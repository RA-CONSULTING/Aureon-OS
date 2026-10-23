@echo off
REM Canonical Aureon launcher for Windows. Live trading is not armed here.
setlocal
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"
python -m aureon.launch.master %*
exit /b %ERRORLEVEL%
