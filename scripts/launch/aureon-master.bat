@echo off
REM Canonical Aureon launcher for Windows. Trading follows exchange keys in .env.
setlocal
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"
python -m aureon.launch.master %*
exit /b %ERRORLEVEL%
