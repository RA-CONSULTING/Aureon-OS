@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1" %*
endlocal
