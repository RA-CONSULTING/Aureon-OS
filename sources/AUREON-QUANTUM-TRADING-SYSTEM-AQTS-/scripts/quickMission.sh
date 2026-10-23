#!/bin/bash
# Quick launcher for ultra-aggressive mission

echo "🔥 AUREON ULTRA-AGGRESSIVE MISSION LAUNCHER 🍯"
echo ""
echo "This will start an 8-hour mission with 50 trade target"
echo "Risk Level: ULTRA-AGGRESSIVE"
echo ""

read -p "Enter starting capital [$1000]: " capital
capital=${capital:-1000}

read -p "Enter mission duration in minutes [480]: " duration
duration=${duration:-480}

read -p "Enter target trades [50]: " trades
trades=${trades:-50}

echo ""
echo "Configuration:"
echo "  Starting Capital: \$$capital"
echo "  Duration: $duration minutes ($(echo "scale=1; $duration/60" | bc) hours)"
echo "  Target Trades: $trades"
echo ""

read -p "Confirm mission start? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Mission aborted."
    exit 1
fi

echo ""
echo "🚀 LAUNCHING MISSION IN 3 SECONDS... 🚀"
sleep 3

export CONFIRM_MISSION=YES
export MISSION_MODE=ULTRA_AGGRESSIVE
export STARTING_CAPITAL=$capital
export MISSION_DURATION=$duration
export TARGET_TRADES=$trades

# Launch mission
npx tsx scripts/ultraAggressiveMission.ts
