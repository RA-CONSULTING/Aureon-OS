@echo off
setlocal
for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
if not exist "%REPO_ROOT%\pyproject.toml" (
  echo Resolved launcher repo root is invalid: "%REPO_ROOT%" 1>&2
  exit /b 1
)
pushd "%REPO_ROOT%" >nul
if errorlevel 1 exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
endlocal & exit /b %EXIT_CODE%
