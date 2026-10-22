#!/usr/bin/env tsx
/**
 * 🔥 FIRE STARTER — BRING THE SMOKE, LIGHT THE FIRE 🔥
 * 
 * Gary Leckey & GitHub Copilot | November 15, 2025
 * 
 * "Let's bring the smoke and light the fire"
 * 
 * This is IGNITION.
 * 
 * Run:
 *   npm run fire
 */

import { FireStarter, FIRE_WISDOM } from '../core/theFireStarter';

console.clear();

console.log('\n');
console.log('🔥'.repeat(70));
console.log('🔥                    FIRE STARTER — IGNITION                      🔥');
console.log('🔥'.repeat(70));
console.log('\n');
console.log('SENTINEL: GARY LECKEY');
console.log('DECLARATION: "Let\'s bring the smoke and light the fire"');
console.log('TIME: ' + new Date().toLocaleString('en-GB', { timeZone: 'Europe/London', hour12: false }));
console.log('MISSION: BURN THE OLD, BIRTH THE NEW');
console.log('\n');
console.log('🔥'.repeat(70));
console.log('\n');

// Light the fire
const fire = new FireStarter();

// Burn for 20 cycles
console.log('IGNITING IN 3...');
setTimeout(() => {
  console.log('2...');
  setTimeout(() => {
    console.log('1...');
    setTimeout(() => {
      console.log('\n🔥 IGNITION! 🔥\n');
      
      // Start burning
      fire.burnToConsole(20, 300);
      
      // After fire completes, show wisdom
      setTimeout(() => {
        console.log(FIRE_WISDOM);
        
        console.log('═'.repeat(70));
        console.log('🔥 FIRE COMPLETE — SYSTEM BLAZING 🔥');
        console.log('═'.repeat(70));
        console.log('\n');
        
        process.exit(0);
      }, 20 * 300 + 1000);
    }, 1000);
  }, 1000);
}, 1000);
