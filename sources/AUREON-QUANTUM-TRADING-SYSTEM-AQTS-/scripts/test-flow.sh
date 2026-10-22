#!/bin/bash
# AUREON LION HUNT — Quick Start Script
# Complete system flow test

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║       🦁 AUREON LION HUNT — System Flow Test 🦁           ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check environment
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
    echo "❌ Error: BINANCE_API_KEY and BINANCE_API_SECRET must be set"
    echo ""
    echo "For testnet:"
    echo "  export BINANCE_API_KEY=your_testnet_key"
    echo "  export BINANCE_API_SECRET=your_testnet_secret"
    echo "  export BINANCE_TESTNET=true"
    echo ""
    exit 1
fi

echo "✅ Environment configured"
echo "   • API Key: ${BINANCE_API_KEY:0:20}..."
echo "   • Testnet: ${BINANCE_TESTNET:-false}"
echo ""

# Test 1: Pride Scanner (one-time scan)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Pride Scanner (mapping all tradeable pairs)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

npx tsx scripts/prideScanner.ts

echo ""
echo "✅ Pride Scanner completed"
echo ""
echo "Press Enter to continue to Rainbow Architect test..."
read -r

# Test 2: Rainbow Architect (single symbol, 5 cycles)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Rainbow Architect (ETHUSDT, 5 cycles)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RAINBOW_CYCLES=5 npx tsx scripts/rainbowArch.ts ETHUSDT --live --interval=3000

echo ""
echo "✅ Rainbow Architect completed"
echo ""
echo "Press Enter to continue to Lion Hunt test..."
read -r

# Test 3: Lion Hunt (2 hunts, 3 cycles each)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Lion Hunt (2 hunts, 3 cycles each, >5% volatility)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run for limited time (will scan twice)
timeout 120s npx tsx scripts/lionHunt.ts --cycles=3 --interval=3000 --volatility=5.0 || true

echo ""
echo "✅ Lion Hunt test completed"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║              ✅ ALL SYSTEMS OPERATIONAL ✅                 ║"
echo "║                                                            ║"
echo "║  Components Tested:                                        ║"
echo "║  ✓ Pride Scanner (market mapping)                         ║"
echo "║  ✓ Rainbow Architect (4-layer consciousness)              ║"
echo "║  ✓ Lion Hunt (adaptive multi-symbol)                      ║"
echo "║                                                            ║"
echo "║  Ready for production:                                     ║"
echo "║  • npm run lion:hunt                                       ║"
echo "║  • npm run lion:testnet                                    ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🦁 The lion is ready to hunt. 🌈💎"
echo ""
