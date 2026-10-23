#!/usr/bin/env node

/**
 * WAR ROOM BRIEF GENERATOR - CLI
 * 
 * Generate and display daily War Room Briefs from the Hive
 * 
 * Usage:
 *   npm run war-room-brief
 *   npm run war-room-brief -- --date 2025-11-23
 *   npm run war-room-brief -- --user "General Quackers" --bot "AUREON-PRIME"
 *   npm run war-room-brief -- --demo
 */

import { HiveWarRoomReporter, generateWarRoomBrief } from '../core/hiveWarRoomReport';
import * as fs from 'fs';
import * as path from 'path';

interface CLIOptions {
  date?: string;
  user?: string;
  botName?: string;
  demo?: boolean;
  output?: string;
  format?: 'text' | 'json' | 'both';
}

function parseArgs(): CLIOptions {
  const args = process.argv.slice(2);
  const options: CLIOptions = {
    format: 'text'
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--date':
      case '-d':
        options.date = args[++i];
        break;
      case '--user':
      case '-u':
        options.user = args[++i];
        break;
      case '--bot':
      case '-b':
        options.botName = args[++i];
        break;
      case '--demo':
        options.demo = true;
        break;
      case '--output':
      case '-o':
        options.output = args[++i];
        break;
      case '--format':
      case '-f':
        options.format = args[++i] as 'text' | 'json' | 'both';
        break;
      case '--help':
      case '-h':
        printHelp();
        process.exit(0);
    }
  }

  return options;
}

function printHelp() {
  console.log(`
╔═══════════════════════════════════════════════════════════════╗
║        WAR ROOM BRIEF GENERATOR - Command Line Tool          ║
╚═══════════════════════════════════════════════════════════════╝

Generate daily intelligence reports from the AUREON Hive.

USAGE:
  npm run war-room-brief [OPTIONS]

OPTIONS:
  -d, --date <date>        Date for the brief (YYYY-MM-DD)
                          Default: today
  
  -u, --user <name>        User name for the brief
                          Default: "Trader"
  
  -b, --bot <name>         Bot name
                          Default: "AUREON-PRIME"
  
  --demo                   Use demo data (sample brief)
  
  -o, --output <path>      Output file path
                          Default: ./reports/war_room_brief_<date>.json
  
  -f, --format <type>      Output format: text, json, or both
                          Default: text
  
  -h, --help              Show this help message

EXAMPLES:
  # Generate brief for today
  npm run war-room-brief

  # Generate brief for specific date
  npm run war-room-brief -- --date 2025-11-23

  # Generate brief with custom user/bot names
  npm run war-room-brief -- --user "General Quackers" --bot "AUREON-ALPHA"

  # View demo brief
  npm run war-room-brief -- --demo

  # Save as JSON
  npm run war-room-brief -- --format json --output ./my-brief.json

╔═══════════════════════════════════════════════════════════════╗
║                    General Quackers Ready 🦆⚡                ║
╚═══════════════════════════════════════════════════════════════╝
  `);
}

async function loadDemoBrief() {
  const demoPath = path.join(__dirname, '..', 'sample_war_room_brief.json');
  if (fs.existsSync(demoPath)) {
    const data = fs.readFileSync(demoPath, 'utf-8');
    return JSON.parse(data);
  }
  throw new Error('Demo brief not found');
}

async function main() {
  const options = parseArgs();

  console.log('\n⚡ AUREON Hive War Room Brief Generator ⚡\n');

  try {
    let brief;

    if (options.demo) {
      console.log('📋 Loading demo brief...\n');
      brief = await loadDemoBrief();
    } else {
      const date = options.date ? new Date(options.date) : new Date();
      const user = options.user || 'Trader';
      const botName = options.botName || 'AUREON-PRIME';

      console.log(`📅 Generating brief for ${date.toISOString().split('T')[0]}...`);
      console.log(`👤 User: ${user}`);
      console.log(`🤖 Bot: ${botName}\n`);

      const reporter = new HiveWarRoomReporter();
      brief = await reporter.generateBrief(date, user, botName);

      // Save brief
      if (options.output || options.format === 'json' || options.format === 'both') {
        const outputPath = options.output || `./reports/war_room_brief_${brief.date}_${brief.botName}.json`;
        const outputDir = path.dirname(outputPath);
        
        if (!fs.existsSync(outputDir)) {
          fs.mkdirSync(outputDir, { recursive: true });
        }
        
        fs.writeFileSync(outputPath, JSON.stringify(brief, null, 2));
        console.log(`💾 Brief saved to: ${outputPath}\n`);
      }
    }

    // Display brief
    if (options.format === 'text' || options.format === 'both') {
      const reporter = new HiveWarRoomReporter();
      const textBrief = reporter.formatBriefAsText(brief);
      console.log(textBrief);
    } else if (options.format === 'json') {
      console.log(JSON.stringify(brief, null, 2));
    }

    console.log('\n✅ Brief generation complete!\n');

  } catch (error) {
    console.error('\n❌ Error generating War Room Brief:');
    console.error(error instanceof Error ? error.message : error);
    console.error('\nTip: Use --demo flag to view a sample brief\n');
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

export { main, parseArgs };
