@echo off
setlocal
cd /d "%~dp0\..\.."

set "AUREON_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%AUREON_PYTHON%" set "AUREON_PYTHON=python"

"%AUREON_PYTHON%" -m aureon.operator.courseops_21_runner --live %*
set "AUREON_EXIT=%ERRORLEVEL%"

endlocal & exit /b %AUREON_EXIT%
