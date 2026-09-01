@echo off
setlocal
for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
set "BOOTSTRAP=%REPO_ROOT%\scripts\bootstrap\protected_bootstrap_v05.py"

if not exist "%PYTHON_EXE%" (
  echo Fixed repository Python executable is unavailable; refusing operation. 1>&2
  endlocal & exit /b 1
)
if not exist "%BOOTSTRAP%" (
  echo Fixed protected bootstrap is unavailable; refusing operation. 1>&2
  endlocal & exit /b 1
)

"%PYTHON_EXE%" -I -S -B "%BOOTSTRAP%" --target-id mind-hub
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%
