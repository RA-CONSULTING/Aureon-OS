@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-AUREON.ps1"
exit /b %ERRORLEVEL%
