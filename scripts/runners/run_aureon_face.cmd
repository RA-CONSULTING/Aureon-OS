@echo off
setlocal

set "REPO_ROOT=%~dp0..\.."
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"
set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Python venv not found: "%PYTHON_EXE%"
  exit /b 1
)

set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%REPO_ROOT%;%REPO_ROOT%\aureon\core;%REPO_ROOT%\aureon\exchanges;%REPO_ROOT%\aureon\data_feeds;%REPO_ROOT%\aureon\monitors;%REPO_ROOT%\aureon\intelligence;%REPO_ROOT%\aureon\queen;%REPO_ROOT%\aureon\autonomous;%PYTHONPATH%"

rem Desktop control is never auto-armed. Live authority is an in-memory lease.
set "AUREON_DESKTOP_LIVE=false"
set "AUREON_DESKTOP_AUTO_ARM=false"

echo.
echo   ======================================
echo     QUEEN SERO IS WAKING UP...
echo     http://localhost:5299
echo   ======================================
echo.

"%PYTHON_EXE%" "%REPO_ROOT%\aureon\autonomous\aureon_face_app.py" %*
