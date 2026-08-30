@echo off
setlocal

set "REPO_ROOT=%~dp0..\.."
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"

set "PYTHON_EXE="
set "PYTHON_PREFIX="
if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
) else (
  where python >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=python"
  ) else (
    where py >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON_EXE=py"
      set "PYTHON_PREFIX=-3"
    )
  )
)

if not defined PYTHON_EXE (
  echo Python 3 was not found.
  exit /b 1
)

set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%REPO_ROOT%;%PYTHONPATH%"

rem No launcher flag can arm desktop control. A live run consumes a one-time
rem AUREON_GUI_CAPABILITY_TOKEN from this process environment only.
set "AUREON_DESKTOP_LIVE=false"
set "AUREON_DESKTOP_AUTO_ARM=false"

"%PYTHON_EXE%" %PYTHON_PREFIX% -m aureon.operator.local_gui_organism %*
