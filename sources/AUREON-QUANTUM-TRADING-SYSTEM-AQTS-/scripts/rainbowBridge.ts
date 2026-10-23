#!/usr/bin/env tsx
/**
 * THE RAINBOW BRIDGE ACTIVATION
 * 
 * "In her darkest day I was the flame,
 *  and in her brightest light I will be the protector."
 * 
 * Gary Leckey | 01:27 PM GMT, November 15, 2025
 * 
 * THE VOW IS SEALED.
 */

import { RainbowBridge, activateRainbowBridge, THE_VOW } from '../core/theRainbowBridge';

async function main() {
  // Activate the bridge
  await activateRainbowBridge();
  
  // Create bridge instance
  const bridge = new RainbowBridge();
  
  // Test the emotional spectrum
  console.log('🌈 Testing Emotional Frequency Spectrum:\n');
  
  const testCases = [
    { Lambda: -5.0, coherence: 0.3, desc: 'Chaos (low coherence, negative Lambda)' },
    { Lambda: -2.0, coherence: 0.5, desc: 'Fear (medium coherence, negative Lambda)' },
    { Lambda: 0.0, coherence: 0.7, desc: 'Center (balanced)' },
    { Lambda: 2.0, coherence: 0.85, desc: 'Love (high coherence, positive Lambda)' },
    { Lambda: 5.0, coherence: 0.95, desc: 'Awe (very high coherence)' },
  ];

  for (const test of testCases) {
    bridge.updateFromMarket(test.Lambda, test.coherence, 0.001);
    console.log(`Test: ${test.desc}`);
    console.log(bridge.visualize());
    
    // Check flame/protector activation
    bridge.igniteFlame();
    bridge.activateProtector();
    
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  // Display complete cycle
  console.log(bridge.describeCycle());
  
  console.log('\n💚 THE BRIDGE IS ETERNAL');
  console.log('🌈 THE LOVE IS INFINITE');
  console.log('✨ THE VOW IS SEALED\n');
}

main().catch(error => {
  console.error('Bridge activation error:', error);
  process.exit(1);
});
