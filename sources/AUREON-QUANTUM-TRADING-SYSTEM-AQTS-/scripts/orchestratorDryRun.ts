#!/usr/bin/env node
import { spawn } from 'node:child_process';

function run(cmd: string, args: string[], env: Record<string,string>): Promise<number> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { stdio: 'inherit', env: { ...process.env, ...env } });
    child.on('close', (code) => resolve(code ?? 0));
  });
}

async function main() {
  const baseEnv = {
    CONFIRM_LIVE_TRADING: 'no',
    DRY_RUN: 'true',
    BINANCE_TESTNET: process.env.BINANCE_TESTNET ?? 'false',
  };

  console.log('\n=== Hummingbird (dry-run) ===');
  await run('npx', ['tsx', 'scripts/hummingbird.ts'], { ...baseEnv, HB_WAIT_FOR_FUNDS: 'no', MAX_MINUTES: '1' });

  console.log('\n=== ArmyAnts (dry-run) ===');
  await run('npx', ['tsx', 'scripts/armyAnts.ts'], { ...baseEnv, ANTS_WAIT_FOR_FUNDS: 'no', ANTS_ROTATIONS: '2', ANTS_SPEND_USDT: '11', ANTS_MAX_MIN: '1' });

  console.log('\n=== LoneWolf (dry-run) ===');
  // Let LoneWolf wait for funds in dry-run mode so it still simulates
  await run('npx', ['tsx', 'scripts/loneWolf.ts'], { ...baseEnv, WOLF_WAIT_FOR_FUNDS: 'yes', WOLF_MAX_MIN: '1' });

  console.log('\n✅ Dry-run suite complete.');
}

main().catch((e) => { console.error('Orchestrator error:', e); process.exit(1); });
