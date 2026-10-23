@echo off
REM AUREON PHI-RADAR STARTER
REM Prime Sentinel: Gary Leckey

echo.
echo ============================================
echo    AUREON PHI-RADAR — AUTONOMOUS TRADER
echo ============================================
echo.

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found. Copying from .env.example
    copy .env.example .env
    echo [ACTION] Edit .env with your Capital.com and Ollama credentials
    pause
    exit /b 1
)

REM Show current status
echo [*] Checking radar status...
python aureon_phi_radar.py --status
echo.

echo [*] Starting phi-scaled monitoring cycle...
echo [*] Press Ctrl+C to stop
echo.

python aureon_phi_radar.py
