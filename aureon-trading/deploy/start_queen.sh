#!/bin/bash
# Queen Power System Startup Script for Digital Ocean
# Ensures Queen's intelligence is fully operational before execution

set -e

echo "🐝 Starting Queen Power System..."

# Wait for state directory
if [ ! -d "/app/state" ]; then
    echo "Creating state directory..."
    mkdir -p /app/state
fi

# Initialize state files if they don't exist
for file in queen_redistribution_state.json power_station_state.json queen_energy_balance.json; do
    if [ ! -f "/app/$file" ]; then
        echo "Initializing $file..."
        echo '{}' > "/app/$file"
    fi
done

# Wait for Command Center to be ready
echo "⏳ Waiting for Command Center..."
sleep 30

# Start Queen Power Redistribution with error handling
echo "⚡ Starting Queen Power Redistribution Engine..."
while true; do
    python -u queen_power_redistribution.py --interval 10 --live 2>&1 || {
        echo "❌ Queen redistribution crashed, restarting in 10s..."
        sleep 10
    }
done
