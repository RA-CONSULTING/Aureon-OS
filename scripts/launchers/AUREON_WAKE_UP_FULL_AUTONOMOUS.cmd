@echo off
setlocal
set "POWERSHELL_PATH=C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL_PATH%" (
  echo Fixed Windows PowerShell executable is unavailable. 1>&2
  exit /b 1
)
for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
if not exist "%REPO_ROOT%\pyproject.toml" (
  echo Resolved launcher repo root is invalid: "%REPO_ROOT%" 1>&2
  exit /b 1
)
pushd "%REPO_ROOT%" >nul
if errorlevel 1 exit /b 1
"%POWERSHELL_PATH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
endlocal & exit /b %EXIT_CODE%
