import { spawn } from 'child_process';
import * as fs from 'fs';
import { loadAccountsFromJson } from './utils/accountLoader';

async function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
  console.log('\n' + '🦁'.repeat(60));
  console.log('  🚀 TACTICAL SQUAD DEPLOYMENT: STAGGERED LAUNCH 🚀');
  console.log('🦁'.repeat(60) + '\n');

  const accounts = loadAccountsFromJson();

  if (accounts.length === 0) {
    console.error('❌ No accounts found in accounts.json!');
    process.exit(1);
  }

  console.log(`📋 FOUND ${accounts.length} AGENTS READY FOR DEPLOYMENT.`);
  console.log(`💰 CONFIGURATION: $10 PER AGENT (Hard Cap)`);
  console.log(`⏱️  STRATEGY: Staggered launch (5s delay) to evade IP Bans.`);
  console.log('─'.repeat(60) + '\n');

  const processes: any[] = [];

  accounts.forEach((account, idx) => account.name ||= `Quacker-${idx + 1}`);

  for (const account of accounts) {
    const label = account.name;
    const safeLabel = label.replace(/[^a-zA-Z0-9_-]/g, '_');
    console.log(`🚀 [T-${accounts.length - processes.length}] Deploying Agent ${label}...`);
    
    const logFile = fs.openSync(`aggressive_assault_${safeLabel}.log`, 'w');
    
    const child = spawn('npx', ['tsx', 'scripts/aggressiveAssault.ts'], {
      env: { 
        ...process.env, 
        BINANCE_API_KEY: account.apiKey, 
        BINANCE_API_SECRET: account.apiSecret,
        // Ensure we don't inherit conflicting env vars if any
      },
      stdio: ['ignore', logFile, logFile], // Redirect stdout/stderr to log file
      detached: true // Let them run independent of this script? No, keep them attached so we can kill them.
    });

    processes.push({ label, pid: child.pid });
    
    console.log(`   ✅ Agent ${label} deployed (PID: ${child.pid}). Logging to aggressive_assault_${safeLabel}.log`);
    
    // STAGGER DELAY
    if (account !== accounts[accounts.length - 1]) {
        console.log(`   ⏳ Waiting 5 seconds before next deployment...`);
        await sleep(5000);
    }
  }

  console.log('\n' + '─'.repeat(60));
  console.log('✅ ALL AGENTS DEPLOYED SUCCESSFULLY.');
  console.log('📡 MONITORING LOGS...');
  console.log('─'.repeat(60) + '\n');
  
  console.log('Press Ctrl+C to stop all agents.');

  // Keep alive to manage processes
  process.on('SIGINT', () => {
    console.log('\n🛑 RECEIVED STOP SIGNAL. TERMINATING ALL AGENTS...');
    processes.forEach(p => {
      try {
        process.kill(p.pid);
        console.log(`   💀 Killed Agent ${p.label} (PID: ${p.pid})`);
      } catch (e) {
        console.log(`   ⚠️ Could not kill Agent ${p.label}: ${(e as any).message}`);
      }
    });
    process.exit(0);
  });
}

main();
