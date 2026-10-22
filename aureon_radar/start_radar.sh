#!/bin/bash
# AUREON PHI-RADAR STARTER
# Prime Sentinel: Gary Leckey

echo ""
echo "============================================"
echo "   AUREON PHI-RADAR — AUTONOMOUS TRADER"
echo "============================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "[WARNING] .env file not found. Copying from .env.example"
    cp .env.example .env
    echo "[ACTION] Edit .env with your Capital.com and Ollama credentials"
    exit 1
fi

# Show current status
echo "[*] Checking radar status..."
python3 aureon_phi_radar.py --status
echo ""

echo "[*] Starting phi-scaled monitoring cycle..."
echo "[*] Press Ctrl+C to stop"
echo ""

python3 aureon_phi_radar.py
