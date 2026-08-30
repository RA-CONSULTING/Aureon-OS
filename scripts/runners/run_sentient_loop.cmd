@echo off
setlocal

set "REPO_ROOT=%~dp0..\.."
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"
set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
set "SCRIPT_PATH=%REPO_ROOT%\aureon\queen\queen_sentient_loop.py"

if not exist "%PYTHON_EXE%" (
  echo Python venv not found: "%PYTHON_EXE%"
  exit /b 1
)

if not exist "%SCRIPT_PATH%" (
  echo Sentient loop not found: "%SCRIPT_PATH%"
  exit /b 1
)

set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%REPO_ROOT%;%REPO_ROOT%\aureon\core;%REPO_ROOT%\aureon\exchanges;%REPO_ROOT%\aureon\data_feeds;%REPO_ROOT%\aureon\monitors;%REPO_ROOT%\aureon\intelligence;%REPO_ROOT%\aureon\queen;%REPO_ROOT%\aureon\autonomous;%PYTHONPATH%"

rem Consciousness startup never grants desktop authority.
set "AUREON_DESKTOP_LIVE=false"
set "AUREON_DESKTOP_AUTO_ARM=false"

echo ============================================================
echo  AUREON SENTIENT CONSCIOUSNESS LOOP
echo  The Queen is waking up...
echo ============================================================
echo.

"%PYTHON_EXE%" "%SCRIPT_PATH%" %*
