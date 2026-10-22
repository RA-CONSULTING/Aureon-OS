@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM AUREON QUAD-ENGINE LAUNCHER — OS + BRIDGE + OLLAMA + RADAR
REM ═══════════════════════════════════════════════════════════════════════════════
REM Starts all four systems:
REM   1. Aureon Bridge (monitors OS, feeds signals)
REM   2. Ollama Switchboard (24/7 cloud API cognitive pipeline)
REM   3. Phi-Radar (auto-hive execution on Capital.com)
REM   4. Dashboard (live status view)
REM ═══════════════════════════════════════════════════════════════════════════════

echo.
echo  ╔══════════════════════════════════════════════════════════════════════════════╗
echo  ║     🐝 AUREON QUAD-ENGINE LAUNCHER 🐝                                        ║
echo  ║                                                                              ║
echo  ║  Engine 1: Aureon OS Bridge      ^(signal extraction^)                      ║
echo  ║  Engine 2: Ollama Cloud Switch   ^(24/7 cognitive pipeline^)                ║
echo  ║  Engine 3: Phi-Radar             ^(auto-hive execution^)                    ║
echo  ║  Engine 4: Live Dashboard        ^(status monitoring^)                      ║
echo  ║                                                                              ║
echo  ║  Data flow: Ollama Cloud ^→ Cognitive ^→ Signals ^→ Radar ^→ Capital LIVE ║
echo  ╚══════════════════════════════════════════════════════════════════════════════╝
echo.

set RADAR_DIR=C:\Users\user\.kimi_openclaw\workspace\aureon_radar

REM ── Start Bridge (Aureon OS signal extraction) ────────────────────────────────
echo  🌉 Starting Aureon OS Bridge...
start "Aureon Bridge" cmd /k "cd /d %RADAR_DIR% && python aureon_bridge.py"
timeout /t 2 /nobreak >nul

REM ── Start Ollama Switchboard (24/7 cognitive pipeline) ────────────────────────
echo  🧠 Starting Ollama Cloud Switchboard (24/7)...
start "Ollama Switchboard" cmd /k "cd /d %RADAR_DIR% && python ollama_switchboard.py"
timeout /t 2 /nobreak >nul

REM ── Start Phi-Radar (auto-hive live trading) ──────────────────────────────────
echo  🐝 Starting Phi-Radar (Capital.com LIVE)...
start "Phi-Radar" cmd /k "cd /d %RADAR_DIR% && python aureon_phi_radar.py"
timeout /t 2 /nobreak >nul

REM ── Start Dashboard ───────────────────────────────────────────────────────────
echo  📊 Starting Live Dashboard...
start "Dashboard" cmd /k "cd /d %RADAR_DIR% && python dashboard.py"

echo.
echo  ✅ All four engines launched!
echo  🌉 Bridge:       Extracts Aureon OS signals
echo  🧠 Ollama:       24/7 cognitive cloud analysis
echo  🐝 Radar:        Auto-executes on Capital.com
echo  📊 Dashboard:    Live status monitor
echo.
echo  Press any key to open trading log monitor...
pause >nul

REM ── Show combined logs ────────────────────────────────────────────────────────
start "Logs" cmd /k "cd /d %RADAR_DIR% && powershell -Command "while(1){Clear-Host; Get-Content radar.log -Tail 15; Write-Host '---'; Get-Content ollama_switchboard.log -Tail 10 -ErrorAction SilentlyContinue; Write-Host '---'; Get-Content aureon_bridge_signals.jsonl -Tail 3 -ErrorAction SilentlyContinue; Write-Host '---'; Get-Content ollama_signals.jsonl -Tail 3 -ErrorAction SilentlyContinue; Start-Sleep 5}"

echo.
echo  🍯 HONEY MODE ACTIVE 🍯
echo.
