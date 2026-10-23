/**
 * LION COMMAND CENTER
 * 
 * The bridge between General Quackers (War Room) and LION scouts.
 * Lions receive their reconnaissance orders and adapt their hunting strategy.
 * 
 * 🦆 General Quackers issues the orders
 * 🦁 LION scouts execute with precision
 */

import { LionReconOrders, HiveWarRoomReporter } from './hiveWarRoomReport';
import * as fs from 'fs';
import * as path from 'path';

export interface LionConfig {
  // Override defaults with War Room orders
  minLighthouseIntensity?: number;
  targetPairs?: string[];
  scanIntervalMs?: number;
  positionSizeMultiplier?: number;
  stopLossMultiplier?: number;
  maxConcurrentTrades?: number;
  aggressionLevel?: 'defensive' | 'normal' | 'aggressive';
}

export class LionCommandCenter {
  private currentOrders: LionReconOrders | null = null;
  private reporter: HiveWarRoomReporter;
  private ordersPath: string;
  
  constructor(ordersPath = './reports/lion_orders.json') {
    this.reporter = new HiveWarRoomReporter();
    this.ordersPath = ordersPath;
  }
  
  /**
   * Fetch latest orders from General Quackers
   */
  async fetchLatestOrders(date: Date = new Date()): Promise<LionReconOrders> {
    console.log('🦁 LION Command Center: Requesting orders from General Quackers...');
    
    try {
      // Generate today's War Room Brief
      const brief = await this.reporter.generateBrief(
        date,
        'LION-SCOUT',
        'AUREON-LION'
      );
      
      this.currentOrders = brief.lionReconOrders;
      
      // Save orders to file for persistence
      const ordersDir = path.dirname(this.ordersPath);
      if (!fs.existsSync(ordersDir)) {
        fs.mkdirSync(ordersDir, { recursive: true });
      }
      
      fs.writeFileSync(
        this.ordersPath,
        JSON.stringify({
          timestamp: new Date().toISOString(),
          fieldStatus: brief.fieldStatus,
          orders: this.currentOrders
        }, null, 2)
      );
      
      console.log('🦆 General Quackers has issued new orders!');
      this.displayOrders(this.currentOrders);
      
      return this.currentOrders;
      
    } catch (error: any) {
      console.warn('⚠️  Could not fetch new orders from General:', error.message);
      console.log('📋 Attempting to load cached orders...');
      return this.loadCachedOrders();
    }
  }
  
  /**
   * Load previously cached orders
   */
  private loadCachedOrders(): LionReconOrders {
    try {
      if (fs.existsSync(this.ordersPath)) {
        const cached = JSON.parse(fs.readFileSync(this.ordersPath, 'utf-8'));
        console.log('✅ Loaded cached orders from', cached.timestamp);
        this.currentOrders = cached.orders;
        return this.currentOrders!;
      }
    } catch (error) {
      console.warn('⚠️  Could not load cached orders');
    }
    
    // Return default conservative orders if nothing available
    console.log('🦁 Using default conservative orders');
    return this.getDefaultOrders();
  }
  
  /**
   * Get default conservative orders (fallback)
   */
  private getDefaultOrders(): LionReconOrders {
    return {
      targetPairs: ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
      scanFrequency: 'conservative',
      entryThreshold: 0.6,
      exitStrategy: 'normal',
      positionSize: 'normal',
      focusAreas: ['High probability setups only', 'Confirmed breakouts'],
      avoidConditions: ['Low volume', 'Choppy conditions'],
      tacticalDirective: '🦁 DEFAULT MODE: Hunt conservatively until General issues new orders.'
    };
  }
  
  /**
   * Convert War Room orders into LionConfig
   */
  translateOrdersToConfig(orders: LionReconOrders): LionConfig {
    const config: LionConfig = {
      targetPairs: orders.targetPairs,
      minLighthouseIntensity: orders.entryThreshold,
      aggressionLevel: this.mapScanFrequencyToAggression(orders.scanFrequency),
      positionSizeMultiplier: this.mapPositionSize(orders.positionSize),
      stopLossMultiplier: this.mapExitStrategy(orders.exitStrategy),
      scanIntervalMs: this.mapScanFrequency(orders.scanFrequency),
      maxConcurrentTrades: this.mapMaxTrades(orders.scanFrequency, orders.positionSize)
    };
    
    return config;
  }
  
  /**
   * Map scan frequency to aggression level
   */
  private mapScanFrequencyToAggression(freq: LionReconOrders['scanFrequency']): 'defensive' | 'normal' | 'aggressive' {
    switch (freq) {
      case 'aggressive': return 'aggressive';
      case 'conservative': return 'defensive';
      default: return 'normal';
    }
  }
  
  /**
   * Map position size to multiplier
   */
  private mapPositionSize(size: LionReconOrders['positionSize']): number {
    switch (size) {
      case 'increased': return 1.5;
      case 'reduced': return 0.5;
      default: return 1.0;
    }
  }
  
  /**
   * Map exit strategy to stop loss multiplier
   */
  private mapExitStrategy(strategy: LionReconOrders['exitStrategy']): number {
    switch (strategy) {
      case 'wide': return 1.5;
      case 'tight': return 0.7;
      default: return 1.0;
    }
  }
  
  /**
   * Map scan frequency to interval milliseconds
   */
  private mapScanFrequency(freq: LionReconOrders['scanFrequency']): number {
    switch (freq) {
      case 'aggressive': return 3000;  // 3 seconds
      case 'conservative': return 10000; // 10 seconds
      default: return 5000; // 5 seconds
    }
  }
  
  /**
   * Map to max concurrent trades
   */
  private mapMaxTrades(freq: LionReconOrders['scanFrequency'], size: LionReconOrders['positionSize']): number {
    let base = 3;
    
    if (freq === 'aggressive') base += 2;
    if (freq === 'conservative') base -= 1;
    
    if (size === 'reduced') base = Math.max(1, base - 1);
    if (size === 'increased') base += 1;
    
    return base;
  }
  
  /**
   * Display orders in console
   */
  private displayOrders(orders: LionReconOrders): void {
    console.log('\n╔═══════════════════════════════════════════════════════════╗');
    console.log('║        🦁 RECONNAISSANCE ORDERS RECEIVED 🦁               ║');
    console.log('╚═══════════════════════════════════════════════════════════╝\n');
    
    console.log('📜 TACTICAL DIRECTIVE:');
    console.log(`   ${orders.tacticalDirective}\n`);
    
    console.log('🎯 MISSION PARAMETERS:');
    console.log(`   • Target Pairs: ${orders.targetPairs.join(', ')}`);
    console.log(`   • Scan Frequency: ${orders.scanFrequency.toUpperCase()}`);
    console.log(`   • Entry Threshold: ${orders.entryThreshold.toFixed(2)} (lighthouse)`);
    console.log(`   • Exit Strategy: ${orders.exitStrategy.toUpperCase()}`);
    console.log(`   • Position Size: ${orders.positionSize.toUpperCase()}`);
    
    console.log('\n✅ FOCUS AREAS:');
    orders.focusAreas.slice(0, 3).forEach(area => {
      console.log(`   ✓ ${area}`);
    });
    
    console.log('\n🚫 AVOID CONDITIONS:');
    orders.avoidConditions.slice(0, 3).forEach(avoid => {
      console.log(`   ✗ ${avoid}`);
    });
    
    console.log('\n' + '═'.repeat(60) + '\n');
  }
  
  /**
   * Check if current conditions match focus areas
   */
  shouldTakeSignal(
    currentLighthouse: number,
    currentCondition: string
  ): { allowed: boolean; reason: string } {
    if (!this.currentOrders) {
      return { allowed: true, reason: 'No orders loaded - default behavior' };
    }
    
    // Check lighthouse threshold
    if (currentLighthouse < this.currentOrders.entryThreshold) {
      return {
        allowed: false,
        reason: `Lighthouse ${currentLighthouse.toFixed(2)} below threshold ${this.currentOrders.entryThreshold.toFixed(2)}`
      };
    }
    
    // Check avoid conditions (simple keyword matching)
    for (const avoid of this.currentOrders.avoidConditions) {
      const keywords = avoid.toLowerCase().split(' ');
      if (keywords.some(kw => currentCondition.toLowerCase().includes(kw))) {
        return {
          allowed: false,
          reason: `Matches avoid condition: ${avoid}`
        };
      }
    }
    
    return { allowed: true, reason: 'Conditions favorable per General\'s orders' };
  }
  
  /**
   * Get summary for logging
   */
  getOrdersSummary(): string {
    if (!this.currentOrders) {
      return 'No active orders';
    }
    
    return `${this.currentOrders.scanFrequency} scan, ${this.currentOrders.positionSize} positions, ${this.currentOrders.exitStrategy} exits`;
  }
  
  /**
   * Export current config for LION scouts
   */
  exportConfig(): LionConfig {
    const orders = this.currentOrders || this.getDefaultOrders();
    return this.translateOrdersToConfig(orders);
  }
}

// Export singleton instance
export const lionCommand = new LionCommandCenter();

/**
 * Convenience function for LION scripts
 */
export async function getLionOrders(): Promise<LionConfig> {
  const orders = await lionCommand.fetchLatestOrders();
  return lionCommand.translateOrdersToConfig(orders);
}
