#!/bin/bash
# 🦁 AUREON AUTOPILOT LAUNCHER 🍯

echo "🦁 AUREON AUTOPILOT LAUNCHER 🍯"
echo ""
echo "This will run 50 trades per day automatically"
echo ""

read -p "How many days to run? [1]: " days
days=${days:-1}

read -p "Confirm autopilot for $days day(s)? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Autopilot cancelled."
    exit 0
fi

echo ""
echo "🚀 LAUNCHING AUTOPILOT FOR $days DAY(S)..."
echo ""

export CONFIRM_AUTOPILOT=YES
export AUTOPILOT_DAYS=$days

python3 scripts/autopilot.py
