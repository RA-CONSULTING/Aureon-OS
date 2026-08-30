@echo off
setlocal

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "STATE_DIR=%REPO_ROOT%\state"
set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
set "AGENT_SCRIPT=%REPO_ROOT%\aureon\autonomous\aureon_unified_voice_agent.py"
set "STOP_FILE=%STATE_DIR%\aureon_voice_agent.stop"
set "OUT_LOG=%STATE_DIR%\aureon_voice_agent_runtime.out.log"
set "ERR_LOG=%STATE_DIR%\aureon_voice_agent_runtime.err.log"
set "SUP_LOG=%STATE_DIR%\aureon_voice_agent_supervisor.log"

if not exist "%REPO_ROOT%\pyproject.toml" (
  echo Resolved voice runner repo root is invalid: "%REPO_ROOT%" 1>&2
  exit /b 1
)
if not exist "%PYTHON_EXE%" (
  echo Python venv not found: "%PYTHON_EXE%" 1>&2
  exit /b 1
)
if not exist "%AGENT_SCRIPT%" (
  echo Voice agent script not found: "%AGENT_SCRIPT%" 1>&2
  exit /b 1
)
cd /d "%REPO_ROOT%"
if errorlevel 1 exit /b 1

if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"

set "AUREON_SPEECH_BACKEND=google_first"
set "AUREON_MIC_DEVICE_INDEX=1"
set "AUREON_GOOGLE_RETRIES=3"
set "AUREON_CAPTURE_RETRIES=3"
set "AUREON_ADJUST_DURATION=1.5"
set "AUREON_AUTO_APPROVE_LIVE_VOICE=true"

:loop
if exist "%STOP_FILE%" (
  echo %date% %time% stop file detected>> "%SUP_LOG%"
  goto :eof
)

echo %date% %time% starting voice runtime>> "%SUP_LOG%"
call "%PYTHON_EXE%" "%AGENT_SCRIPT%" --mic 1>> "%OUT_LOG%" 2>> "%ERR_LOG%"
echo %date% %time% runtime exited errorlevel=%errorlevel%>> "%SUP_LOG%"
timeout /t 3 /nobreak >nul
goto loop
