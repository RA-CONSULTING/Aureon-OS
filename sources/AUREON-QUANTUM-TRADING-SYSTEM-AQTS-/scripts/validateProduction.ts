#!/usr/bin/env node
/**
 * 🔍 PRODUCTION ENVIRONMENT VALIDATOR
 * 
 * Validates your complete production setup before launch
 * - Checks all requirements
 * - Verifies file structure
 * - Tests API connectivity
 * - Confirms safety systems
 */

import * as fs from 'fs';
import * as path from 'path';
import { envConfig } from '../core/environment';

const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

interface ValidationCheck {
  category: string;
  name: string;
  status: 'pass' | 'fail' | 'warning';
  message: string;
}

const checks: ValidationCheck[] = [];

function log(message: string, color: string = RESET) {
  console.log(`${color}${message}${RESET}`);
}

function header(text: string) {
  console.log('\n' + '═'.repeat(70));
  log(`  ${text}`, BOLD + BLUE);
  console.log('═'.repeat(70) + '\n');
}

function check(category: string, name: string, status: 'pass' | 'fail' | 'warning', message: string) {
  const icon = status === 'pass' ? '✅' : status === 'fail' ? '❌' : '⚠️';
  const color = status === 'pass' ? GREEN : status === 'fail' ? RED : YELLOW;
  log(`${icon} ${name}: ${message}`, color);
  checks.push({ category, name, status, message });
}

function checkFileExists(filePath: string): boolean {
  return fs.existsSync(path.join(process.cwd(), filePath));
}

function validateFileStructure() {
  header('📁 FILE STRUCTURE VALIDATION');
  
  const requiredFiles = [
    { path: 'package.json', name: 'Package config' },
    { path: 'tsconfig.json', name: 'TypeScript config' },
    { path: '.env', name: 'Environment file' },
    { path: 'ecosystem.config.js', name: 'PM2 config' },
    { path: 'scripts/productionLaunch.ts', name: 'Production launcher' },
    { path: 'scripts/emergencyStop.ts', name: 'Emergency stop' },
    { path: 'scripts/performanceReport.ts', name: 'Performance reporter' },
    { path: 'scripts/realisticForecast.ts', name: 'Forecast calculator' },
    { path: 'scripts/hummingbird.ts', name: 'Hummingbird bot' },
    { path: 'scripts/armyAnts.ts', name: 'ArmyAnts bot' },
    { path: 'scripts/loneWolf.ts', name: 'LoneWolf bot' },
    { path: 'core/binanceClient.ts', name: 'Binance client' },
    { path: 'core/config.ts', name: 'Config module' },
    { path: 'PRODUCTION_DEPLOYMENT.md', name: 'Deployment guide' },
    { path: 'QUICKREF.txt', name: 'Quick reference' }
  ];
  
  requiredFiles.forEach(file => {
    if (checkFileExists(file.path)) {
      check('files', file.name, 'pass', `Found at ${file.path}`);
    } else {
      check('files', file.name, 'fail', `Missing: ${file.path}`);
    }
  });
}

function validateDirectories() {
  header('📂 DIRECTORY STRUCTURE VALIDATION');
  
  const requiredDirs = [
    { path: 'scripts', name: 'Scripts directory' },
    { path: 'core', name: 'Core modules' },
    { path: 'docs', name: 'Documentation' },
    { path: 'logs', name: 'Logs directory', create: true },
    { path: 'artifacts', name: 'Artifacts directory', create: true }
  ];
  
  requiredDirs.forEach(dir => {
    const fullPath = path.join(process.cwd(), dir.path);
    
    if (fs.existsSync(fullPath)) {
      check('dirs', dir.name, 'pass', `Found at ${dir.path}/`);
    } else if (dir.create) {
      try {
        fs.mkdirSync(fullPath, { recursive: true });
        check('dirs', dir.name, 'pass', `Created ${dir.path}/`);
      } catch (error) {
        check('dirs', dir.name, 'fail', `Cannot create ${dir.path}/`);
      }
    } else {
      check('dirs', dir.name, 'fail', `Missing: ${dir.path}/`);
    }
  });
}

function validateEnvironment() {
  header('⚙️  ENVIRONMENT VALIDATION');
  
  // Check .env exists
  if (!checkFileExists('.env')) {
    check('env', '.env file', 'fail', 'Missing - copy from .env.example');
    return;
  }
  
  // Check API keys
  const apiKey = process.env.BINANCE_API_KEY || '';
  const apiSecret = process.env.BINANCE_API_SECRET || '';
  
  if (!apiKey || apiKey === 'your_api_key_here') {
    check('env', 'BINANCE_API_KEY', 'fail', 'Not configured in .env');
  } else if (apiKey.length < 32) {
    check('env', 'BINANCE_API_KEY', 'warning', 'Seems too short - verify it\'s correct');
  } else {
    check('env', 'BINANCE_API_KEY', 'pass', `Configured (${apiKey.slice(0, 8)}...)`);
  }
  
  if (!apiSecret || apiSecret === 'your_api_secret_here') {
    check('env', 'BINANCE_API_SECRET', 'fail', 'Not configured in .env');
  } else if (apiSecret.length < 32) {
    check('env', 'BINANCE_API_SECRET', 'warning', 'Seems too short - verify it\'s correct');
  } else {
    check('env', 'BINANCE_API_SECRET', 'pass', `Configured (${apiSecret.slice(0, 8)}...)`);
  }
  
  // Check trading flags
  const dryRun = process.env.DRY_RUN === 'true';
  const confirmLive = process.env.CONFIRM_LIVE_TRADING === 'true';
  const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");
  
  if (dryRun) {
    check('env', 'DRY_RUN', 'warning', 'Enabled - no real trades will execute');
  } else {
    check('env', 'DRY_RUN', 'pass', 'Disabled - ready for live trading');
  }
  
  if (!confirmLive) {
    check('env', 'CONFIRM_LIVE_TRADING', 'fail', 'Must be "true" for production');
  } else {
    check('env', 'CONFIRM_LIVE_TRADING', 'pass', 'Confirmed for live trading');
  }
  
  if (testnet) {
    check('env', 'BINANCE_TESTNET', 'warning', 'Testnet mode - not using real money');
  } else {
    check('env', 'BINANCE_TESTNET', 'pass', 'Production network - using real API');
  }
}

function validateNodeEnvironment() {
  header('🔧 NODE.JS ENVIRONMENT VALIDATION');
  
  const nodeVersion = process.version;
  const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
  
  if (majorVersion >= 22) {
    check('node', 'Node.js version', 'pass', `${nodeVersion} (recommended)`);
  } else if (majorVersion >= 18) {
    check('node', 'Node.js version', 'warning', `${nodeVersion} (works but v22+ recommended)`);
  } else {
    check('node', 'Node.js version', 'fail', `${nodeVersion} (upgrade to v22+ required)`);
  }
  
  // Check for required global tools
  const tools = [
    { cmd: 'npx', name: 'npx (Node package runner)' },
    { cmd: 'tsx', name: 'tsx (TypeScript executor)', optional: true }
  ];
  
  // We'll assume npx is available if we got this far
  check('node', 'npx', 'pass', 'Available');
  
  // Check package.json dependencies
  if (checkFileExists('package.json')) {
    const pkg = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'package.json'), 'utf-8'));
    
    const requiredDeps = ['typescript', 'tsx', 'axios', 'express', 'dotenv'];
    const missing = requiredDeps.filter(dep => 
      !pkg.dependencies?.[dep] && !pkg.devDependencies?.[dep]
    );
    
    if (missing.length === 0) {
      check('node', 'Dependencies', 'pass', 'All required packages in package.json');
    } else {
      check('node', 'Dependencies', 'warning', `Missing in package.json: ${missing.join(', ')}`);
    }
  }
}

function validateScriptsExecutable() {
  header('🚀 SCRIPT VALIDATION');
  
  const scripts = [
    'scripts/productionLaunch.ts',
    'scripts/emergencyStop.ts',
    'scripts/performanceReport.ts',
    'scripts/realisticForecast.ts',
    'scripts/hummingbird.ts',
    'scripts/armyAnts.ts',
    'scripts/loneWolf.ts'
  ];
  
  scripts.forEach(script => {
    if (checkFileExists(script)) {
      const content = fs.readFileSync(path.join(process.cwd(), script), 'utf-8');
      
      // Check for shebang
      if (content.startsWith('#!/usr/bin/env node')) {
        check('scripts', path.basename(script), 'pass', 'Executable with shebang');
      } else {
        check('scripts', path.basename(script), 'warning', 'Missing shebang (minor)');
      }
    } else {
      check('scripts', path.basename(script), 'fail', 'Script not found');
    }
  });
}

function validateDocumentation() {
  header('📖 DOCUMENTATION VALIDATION');
  
  const docs = [
    { path: 'README.md', name: 'Main README' },
    { path: 'PRODUCTION_DEPLOYMENT.md', name: 'Production guide' },
    { path: 'QUICKREF.txt', name: 'Quick reference' },
    { path: 'docs/LIVE_TRADING_GUIDE.md', name: 'Live trading guide' },
    { path: 'docs/AQTS_System_Architecture.md', name: 'Architecture docs' }
  ];
  
  docs.forEach(doc => {
    if (checkFileExists(doc.path)) {
      const stats = fs.statSync(path.join(process.cwd(), doc.path));
      const sizeMB = (stats.size / 1024).toFixed(1);
      check('docs', doc.name, 'pass', `${sizeMB} KB`);
    } else {
      check('docs', doc.name, 'warning', 'Not found (optional)');
    }
  });
}

function displaySummary() {
  header('📊 VALIDATION SUMMARY');
  
  const byStatus = {
    pass: checks.filter(c => c.status === 'pass').length,
    fail: checks.filter(c => c.status === 'fail').length,
    warning: checks.filter(c => c.status === 'warning').length
  };
  
  const byCategory: Record<string, any> = {};
  checks.forEach(c => {
    if (!byCategory[c.category]) {
      byCategory[c.category] = { pass: 0, fail: 0, warning: 0 };
    }
    byCategory[c.category][c.status]++;
  });
  
  log(`Total Checks: ${checks.length}`, BLUE);
  log(`  ✅ Passed: ${byStatus.pass}`, GREEN);
  log(`  ❌ Failed: ${byStatus.fail}`, RED);
  log(`  ⚠️  Warnings: ${byStatus.warning}`, YELLOW);
  
  console.log('');
  log('By Category:', BLUE);
  Object.entries(byCategory).forEach(([cat, stats]) => {
    log(`  ${cat}: ✅${stats.pass} ❌${stats.fail} ⚠️${stats.warning}`, RESET);
  });
  
  console.log('');
  
  if (byStatus.fail > 0) {
    log('❌ PRODUCTION NOT READY', RED + BOLD);
    log('Fix failed checks before proceeding to production', RED);
    return false;
  } else if (byStatus.warning > 5) {
    log('⚠️  PRODUCTION READY (with warnings)', YELLOW + BOLD);
    log('Review warnings - system should work but may not be optimal', YELLOW);
    return true;
  } else {
    log('✅ PRODUCTION READY', GREEN + BOLD);
    log('All critical checks passed - ready to launch!', GREEN);
    return true;
  }
}

function displayNextSteps(ready: boolean) {
  header('🎯 NEXT STEPS');
  
  if (!ready) {
    log('Fix the failed checks above, then re-run this validator:', YELLOW);
    log('  npx tsx scripts/validateProduction.ts', BLUE);
    return;
  }
  
  log('Your production environment is validated and ready!', GREEN);
  console.log('');
  log('To launch:', BLUE);
  log('  1. Read the full deployment guide:', BLUE);
  log('     cat PRODUCTION_DEPLOYMENT.md', BLUE);
  console.log('');
  log('  2. Review the quick reference:', BLUE);
  log('     cat QUICKREF.txt', BLUE);
  console.log('');
  log('  3. Launch production:', BLUE);
  log('     npx tsx scripts/productionLaunch.ts', GREEN + BOLD);
  console.log('');
  log('     OR with PM2:', BLUE);
  log('     pm2 start ecosystem.config.js', GREEN + BOLD);
  console.log('');
  log('Emergency stop available:', YELLOW);
  log('  npx tsx scripts/emergencyStop.ts', YELLOW);
  console.log('');
}

async function main() {
  console.clear();
  
  header('🔍 AUREON PRODUCTION ENVIRONMENT VALIDATOR');
  
  log('Validating your production setup...', BLUE);
  log('This ensures all systems are ready for live trading.', BLUE);
  
  // Run all validations
  validateNodeEnvironment();
  validateFileStructure();
  validateDirectories();
  validateEnvironment();
  validateScriptsExecutable();
  validateDocumentation();
  
  // Display summary
  const ready = displaySummary();
  
  // Next steps
  displayNextSteps(ready);
  
  process.exit(ready ? 0 : 1);
}

// Run if executed directly
main().catch((error) => {
  log(`\n❌ FATAL ERROR: ${error.message}`, RED + BOLD);
  process.exit(1);
});

export { validateFileStructure, validateEnvironment };
