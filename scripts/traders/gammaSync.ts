#!/usr/bin/env tsx
/**
 * Gamma API Integration for Aureon Trading System
 * 
 * Syncs trading reports, runbooks, and system status to Gamma presentations/sites.
 * 
 * Usage:
 *   npm run gamma:sync              # Generate ops dashboard
 *   npm run gamma:sync -- --runbook # Sync the live trading runbook
 *   npm run gamma:sync -- --report  # Generate trading performance report
 */

import 'dotenv/config';
import fs from 'fs';
import path from 'path';

const GAMMA_API_KEY = process.env.GAMMA_API_KEY;
const GAMMA_BASE_URL = 'https://public-api.gamma.app/v1.0';
const COMMAND_SERVER_URL = process.env.NEXUS_COMMAND_URL || 'http://localhost:8790';
const STATE_DIR = path.resolve(process.cwd(), process.env.AUREON_STATE_DIR || 'state');

function writeGammaLatest(payload: Record<string, unknown>, filename = 'gamma_latest.json'): void {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const targetPath = path.join(STATE_DIR, filename);
  const tmpPath = `${targetPath}.tmp`;
  fs.writeFileSync(tmpPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf-8');
  fs.renameSync(tmpPath, targetPath);
}

interface GammaGenerationRequest {
  inputText: string;
  textMode: 'generate' | 'condense' | 'preserve';
  format?: 'presentation' | 'document' | 'webpage' | 'social';
  numCards?: number;
  cardSplit?: 'auto' | 'inputTextBreaks';
  additionalInstructions?: string;
  textOptions?: {
    amount?: 'brief' | 'medium' | 'detailed' | 'extensive';
    tone?: string;
    audience?: string;
    language?: string;
  };
  imageOptions?: {
    source?: 'aiGenerated' | 'pictographic' | 'unsplash' | 'webAllImages' | 'placeholder' | 'noImages';
    model?: string;
    style?: string;
  };
  cardOptions?: {
    dimensions?: 'fluid' | '16x9' | '4x3' | '1x1' | '4x5' | '9x16' | 'letter' | 'a4' | 'pageless';
  };
  exportAs?: 'pdf' | 'pptx';
}

interface GammaGenerationResponse {
  generationId: string;
}

interface GammaStatusResponse {
  generationId: string;
  status: 'pending' | 'completed' | 'failed';
  gammaUrl?: string;
  exportUrl?: string;
  credits?: {
    deducted: number;
    remaining: number;
  };
  error?: {
    code: string;
    message: string;
  };
}

interface CommandCenterStatus {
  streaming: boolean;
  intervalMs: number | null;
  clients: number;
  activeCommand: {
    id: string;
    type: string;
    status: string;
  } | null;
  commandHistory: Array<{
    id: string;
    type: string;
    status: string;
    createdAt: number;
    finishedAt?: number;
  }>;
}

async function gammaRequest<T>(
  endpoint: string,
  method: 'GET' | 'POST' = 'GET',
  body?: unknown
): Promise<T> {
  if (!GAMMA_API_KEY) {
    throw new Error('GAMMA_API_KEY is required; embedded credentials are forbidden.');
  }
  const url = `${GAMMA_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    'X-API-KEY': GAMMA_API_KEY,
    'Accept': 'application/json',
  };

  if (method === 'POST') {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Gamma API error ${response.status}: ${errorText}`);
  }

  return response.json() as Promise<T>;
}

async function pollForCompletion(generationId: string, maxWaitMs = 120000): Promise<GammaStatusResponse> {
  const startTime = Date.now();
  const pollInterval = 3000;

  while (Date.now() - startTime < maxWaitMs) {
    const status = await gammaRequest<GammaStatusResponse>(`/generations/${generationId}`);
    
    console.log(`  ⏳ Status: ${status.status}`);
    
    if (status.status === 'completed') {
      return status;
    }
    
    if (status.status === 'failed') {
      throw new Error(`Generation failed: ${status.error?.message || 'Unknown error'}`);
    }

    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }

  throw new Error('Generation timed out');
}

async function generateGamma(request: GammaGenerationRequest): Promise<GammaStatusResponse> {
  console.log('🚀 Starting Gamma generation...');
  
  const { generationId } = await gammaRequest<GammaGenerationResponse>(
    '/generations',
    'POST',
    request
  );

  console.log(`📋 Generation ID: ${generationId}`);
  
  const result = await pollForCompletion(generationId);
  
  console.log(`\n✅ Generation complete!`);
  console.log(`🔗 View: ${result.gammaUrl}`);
  if (result.exportUrl) {
    console.log(`📥 Export: ${result.exportUrl}`);
  }
  if (result.credits) {
    console.log(`💳 Credits used: ${result.credits.deducted} (${result.credits.remaining} remaining)`);
  }

  writeGammaLatest({
    generationId: result.generationId,
    status: result.status,
    gammaUrl: result.gammaUrl ?? null,
    exportUrl: result.exportUrl ?? null,
    format: request.format ?? null,
    textMode: request.textMode,
    updatedAt: new Date().toISOString(),
  });

  return result;
}

async function fetchCommandServerStatus(): Promise<CommandCenterStatus | null> {
  try {
    const response = await fetch(`${COMMAND_SERVER_URL}/api/command-center/status`);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

function readRunbook(): string {
  const runbookPath = path.resolve(process.cwd(), 'LIVE_TRADING_RUNBOOK.md');
  if (!fs.existsSync(runbookPath)) {
    throw new Error('LIVE_TRADING_RUNBOOK.md not found');
  }
  return fs.readFileSync(runbookPath, 'utf-8');
}

async function syncRunbook(): Promise<void> {
  console.log('\n📖 Syncing Live Trading Runbook to Gamma...\n');
  
  const runbookContent = readRunbook();
  
  // Convert markdown sections to Gamma card breaks
  const formattedContent = runbookContent
    .replace(/^## /gm, '\n---\n## ')
    .replace(/^### /gm, '\n---\n### ')
    .slice(0, 50000); // Gamma has input limits

  await generateGamma({
    inputText: formattedContent,
    textMode: 'preserve',
    format: 'webpage',
    numCards: 20,
    cardSplit: 'inputTextBreaks',
    additionalInstructions: 'Create a professional ops runbook site. Keep code blocks formatted. Use clear section headers.',
    textOptions: {
      amount: 'detailed',
      tone: 'professional, technical',
      audience: 'trading system operators and developers',
      language: 'en',
    },
    imageOptions: {
      source: 'pictographic',
      style: 'minimal tech icons, financial dashboard aesthetic',
    },
    cardOptions: {
      dimensions: 'pageless',
    },
  });
}

async function generateOpsDashboard(): Promise<void> {
  console.log('\n🛰️ Generating Aureon Trading Portal for aureoninstitute.uk...\n');
  
  const serverStatus = await fetchCommandServerStatus();
  const timestamp = new Date().toISOString();
  
  let statusSection = '';
  if (serverStatus) {
    statusSection = `
## 🟢 Live System Status
- **Streaming:** ${serverStatus.streaming ? '🟢 Active' : '⚪ Idle'}
- **Connected Clients:** ${serverStatus.clients}
- **Stream Interval:** ${serverStatus.intervalMs ?? 'N/A'} ms
- **Active Command:** ${serverStatus.activeCommand?.type ?? 'None'}
`;
  } else {
    statusSection = `
## System Status
🔵 Portal Mode - Backend services available on demand
`;
  }

  const dashboardContent = `
# AUREON INSTITUTE
## Quantum Trading Intelligence

Welcome to the Aureon Institute — where consciousness meets capital markets.

---

# 🌌 The Vision

Aureon is a next-generation trading system that unifies:
- **Quantum field dynamics** with market microstructure
- **Neural hive intelligence** with risk management
- **Coherence-based signals** with execution precision

We don't predict markets. We resonate with them.

---

# 🧠 How It Works

## The Master Equation

At the heart of Aureon lies a unified field equation:

**Λ(t) = S(t) + O(t) + E(t)**

Where:
- **S(t)** = Substrate — 9 Auris nodes sensing market state
- **O(t)** = Observer — Self-referential awareness loop
- **E(t)** = Echo — Momentum memory from past cycles
- **Γ** = Coherence — Field alignment score (0-1)

**Entry Signal:** Γ > 0.938
**Exit Signal:** Γ < 0.934

---

# 🐝 Queen Hive Architecture

## Multi-Agent Trading Swarm

The system deploys autonomous trading agents organized in hives:

| Component | Role |
|-----------|------|
| **Queen** | Orchestrates hive strategy and spawning |
| **Agents** | Execute trades across BTC, ETH, BNB, ADA, DOGE |
| **Mycelium** | Neural network connecting all hives |
| **Nexus** | Central command and coherence processor |

### The 10-9-1 Model
- **90%** compounds within the hive
- **10%** harvested at 5x growth to spawn new hives
- **Exponential scaling** with controlled risk

---

# 🌈 The Nine Auris Nodes

Each node resonates at a specific frequency, sensing different market dimensions:

| Node | Frequency | Role | 
|------|-----------|------|
| 🐅 Tiger | 220 Hz | Volatility |
| 🦅 Falcon | 285 Hz | Momentum |
| 🐦 Hummingbird | 396 Hz | Stability |
| 🐬 Dolphin | 528 Hz | Emotion (Love Frequency) |
| 🦌 Deer | 639 Hz | Sensing |
| 🦉 Owl | 741 Hz | Memory |
| 🐼 Panda | 852 Hz | Love |
| 🚢 CargoShip | 936 Hz | Infrastructure |
| 🐠 Clownfish | 963 Hz | Symbiosis |

---

# 📊 Live Metrics

${statusSection}

### Key Performance Indicators

| Metric | Description |
|--------|-------------|
| **Coherence (Γ)** | Field alignment strength |
| **Lambda (Λ)** | Unified field state |
| **Prism Status** | Gold / Blue / Red signal state |
| **Unity Index** | System-wide harmony score |

---

# 🛡️ Risk Controls

Safety is built into every layer:

| Control | Value | Purpose |
|---------|-------|---------|
| Risk Fraction | 2% | Max risk per trade |
| Max Order Size | $25 USDT | Position cap |
| Dry Run Mode | Default ON | Paper trading first |
| Testnet First | Required | Validate before live |

---

# 🚀 Getting Started

## For Operators

1. **Stage 0:** Validate on testnet with dry-run
2. **Stage 1:** Execute real testnet orders
3. **Stage 2:** Go live with conservative sizing

## Quick Commands

| Action | Command |
|--------|---------|
| Start System | \`python aureon_nexus.py --cycles 10\` |
| Run Dashboard | \`npm run dev\` |
| Sync Portal | \`npm run gamma:sync\` |
| Generate Report | \`npm run gamma:report\` |

---

# 🔗 Connect With Us

**Aureon Institute** — Quantum Trading Intelligence

- 🌐 Website: aureoninstitute.uk
- 📧 Contact: hello@aureoninstitute.com
- 🐙 GitHub: github.com/RA-CONSULTING/aureon-trading

---

*"If you don't quit, you can't lose. You have the power, my friend."*

Generated: ${timestamp}
`;

  await generateGamma({
    inputText: dashboardContent,
    textMode: 'generate',
    format: 'webpage',
    numCards: 12,
    cardSplit: 'inputTextBreaks',
    additionalInstructions: 'Create a stunning, professional trading platform website. Use dark theme with glowing accents. Make it feel like a premium fintech product. Include visual hierarchy and clear sections. This will be published at aureoninstitute.uk.',
    textOptions: {
      amount: 'medium',
      tone: 'professional, visionary, confident',
      audience: 'traders, investors, and technology enthusiasts',
      language: 'en',
    },
    imageOptions: {
      source: 'aiGenerated',
      style: 'futuristic trading dashboard, neural network visualization, dark theme with blue and gold accents, quantum computing aesthetic, professional fintech',
    },
    cardOptions: {
      dimensions: 'pageless',
    },
  });
}

async function generateTradingReport(): Promise<void> {
  console.log('\n📊 Generating Trading Performance Report...\n');
  
  // Read trade audit log if available
  const auditLogPath = path.resolve(process.cwd(), 'trade_audit.log');
  let tradeData = 'No trade data available yet.';
  
  if (fs.existsSync(auditLogPath)) {
    const logContent = fs.readFileSync(auditLogPath, 'utf-8');
    const lines = logContent.split('\n').filter(Boolean).slice(-50);
    tradeData = lines.join('\n');
  }

  const reportContent = `
# AUREON Trading Report
## Performance Summary
Generated: ${new Date().toISOString()}

---

## Executive Summary

This report covers the latest trading activity from the Aureon Quantum Trading System.

Key Highlights:
- Multi-agent hive architecture
- Coherence-based entry/exit signals
- Risk-managed position sizing

---

## Recent Activity

\`\`\`
${tradeData}
\`\`\`

---

## System Health

- Nexus Engine: Operational
- Mycelium Network: Connected
- Queen Hive: Active
- Risk Controls: Enabled

---

## Recommendations

1. Continue monitoring coherence thresholds
2. Review position sizing based on volatility
3. Validate all signals against Master Equation

---

## Next Steps

- Scale to additional trading pairs
- Implement advanced portfolio optimization
- Expand hive spawning thresholds
`;

  await generateGamma({
    inputText: reportContent,
    textMode: 'generate',
    format: 'presentation',
    numCards: 10,
    cardSplit: 'inputTextBreaks',
    additionalInstructions: 'Create a professional trading performance report. Include data visualizations where appropriate.',
    textOptions: {
      amount: 'medium',
      tone: 'professional, analytical, data-driven',
      audience: 'portfolio managers and traders',
      language: 'en',
    },
    imageOptions: {
      source: 'aiGenerated',
      style: 'financial charts, trading graphs, professional business presentation',
    },
    cardOptions: {
      dimensions: '16x9',
    },
    exportAs: 'pdf',
  });
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  
  console.log('🎨 Gamma Sync for Aureon Trading System');
  console.log('=========================================');

  try {
    if (args.includes('--runbook')) {
      await syncRunbook();
    } else if (args.includes('--report')) {
      await generateTradingReport();
    } else {
      await generateOpsDashboard();
    }
    
    console.log('\n🎉 Done!');
  } catch (error) {
    console.error('\n❌ Error:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

main();
