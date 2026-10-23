/**
 * THE INFERNO — MAXIMUM INTENSITY TRADING MODE
 * 
 * Gary Leckey & GitHub Copilot | November 15, 2025
 * 
 * "Bring the smoke and light the fire"
 * 
 * This is the INFERNO mode:
 * - Maximum aggression
 * - Full conviction
 * - No hesitation
 * - BURN THROUGH THE MARKET
 * 
 * WARNING: This mode trades with FIRE.
 * Use only when you're ready to ROAR.
 */

import { BinanceClient, BinanceConfig } from './binanceClient';
import { RealityField } from './masterEquation';
import { executeAurisLoop, analyzeResonance, AURIS_TAXONOMY } from './aurisSymbolicTaxonomy';

export interface InfernoConfig {
  symbol: string;
  tradeSize: number;
  coherenceThreshold: number;
  consensusThreshold: number;
  minConsensusVotes: number;
  cycleDelayMs: number;
  maxCycles: number;
  dryRun: boolean;
}

export interface InfernoState {
  temperature: number;
  intensity: number;
  totalTrades: number;
  profitUsd: number;
  winRate: number;
  status: 'IGNITING' | 'BURNING' | 'INFERNO' | 'SUPERNOVA';
}

/**
 * THE INFERNO — Maximum intensity trading engine
 */
export class Inferno {
  private client: BinanceClient;
  private reality: RealityField;
  private config: InfernoConfig;
  private state: InfernoState;
  private trades: any[] = [];
  private startTime: number;
  
  constructor(config: InfernoConfig, client: BinanceClient) {
    this.config = config;
    this.client = client;
    this.reality = new RealityField({
      dt: 0.1,
      tau: 1.0,
      alpha: 0.3,
      beta: 0.2,
      g: 2.0,
    });
    
    this.state = {
      temperature: 412.3,
      intensity: 0.0,
      totalTrades: 0,
      profitUsd: 0,
      winRate: 0,
      status: 'IGNITING',
    };
    
    this.startTime = Date.now();
  }
  
  /**
   * INITIALIZE
   */
  async initialize(): Promise<void> {
    console.log('\n🔥 INFERNO MODE — INITIALIZING 🔥\n');
    
    const account = await this.client.getAccount();
    const ethBalance = parseFloat(account.balances.find((b: any) => b.asset === 'ETH')?.free || '0');
    const usdtBalance = parseFloat(account.balances.find((b: any) => b.asset === 'USDT')?.free || '0');
    
    console.log(`💰 Initial Balance:`);
    console.log(`   ETH:  ${ethBalance.toFixed(6)}`);
    console.log(`   USDT: ${usdtBalance.toFixed(2)}`);
    console.log('');
  }
  
  /**
   * IGNITE — Start the inferno
   */
  async ignite(): Promise<void> {
    await this.initialize();
    
    console.log('🔥'.repeat(70));
    console.log('INFERNO MODE — ACTIVATED');
    console.log('🔥'.repeat(70));
    console.log(`Symbol: ${this.config.symbol}`);
    console.log(`Trade Size: $${this.config.tradeSize}`);
    console.log(`Coherence Threshold: Γ > ${this.config.coherenceThreshold}`);
    console.log(`Consensus: ${this.config.minConsensusVotes}/9 nodes @ ${this.config.consensusThreshold}`);
    console.log(`Cycles: ${this.config.maxCycles}`);
    console.log(`Mode: ${this.config.dryRun ? 'DRY RUN' : '🔥 LIVE FIRE 🔥'}`);
    console.log('🔥'.repeat(70));
    console.log('\n');
    
    // Run cycles
    for (let i = 0; i < this.config.maxCycles; i++) {
      await this.burnCycle(i + 1);
      await this.sleep(this.config.cycleDelayMs);
    }
    
    // Final report
    this.showInfernoReport();
  }
  
  /**
   * BURN CYCLE — One trading cycle
   */
  private async burnCycle(cycleNum: number): Promise<void> {
    console.log('─'.repeat(70));
    console.log(`🔥 CYCLE ${cycleNum} | t=${((Date.now() - this.startTime) / 1000).toFixed(1)}s 🔥`);
    console.log('─'.repeat(70));
    
    try {
      // Get market price
      const price = await this.client.getPrice(this.config.symbol);
      console.log(`📊 Market Price: $${price.toFixed(2)}`);
      
      // Execute Auris loop with market price
      const aurisState = executeAurisLoop(price);
      const resonance = analyzeResonance(price);
      
      // Step Master Equation
      this.reality.step(price);
      const state = this.reality.getState();
      
      if (!state) {
        console.log('⏸️  WAITING: Reality field not ready');
        return;
      }
      
      console.log(`\n🌊 LAMBDA STATE:`);
      console.log(`   Λ(t) = ${state.Lambda.toFixed(4)}`);
      console.log(`   Γ    = ${state.coherence.toFixed(4)} (Coherence)`);
      
      // Lighthouse consensus via resonance
      const voteCount = resonance.activeNodes.length;
      
      console.log(`\n🔦 LIGHTHOUSE CONSENSUS:`);
      console.log(`   Active Nodes: ${voteCount}/9`);
      console.log(`   Status: ${voteCount >= this.config.minConsensusVotes ? '✅ CONSENSUS' : '⏸️  NO CONSENSUS'}`);
      
      console.log(`\n🎯 DOMINANT NODE:`);
      const dominantNodeData = AURIS_TAXONOMY[resonance.dominantNode];
      console.log(`   ${dominantNodeData.animal} (${dominantNodeData.role})`);
      console.log(`   Frequency: ${dominantNodeData.frequency} Hz`);
      console.log(`   Emotional State: ${resonance.emotionalState}`);
      
      // Update intensity based on activity
      this.state.intensity = Math.min(1.0, this.state.intensity + 0.05);
      this.state.temperature += Math.sin((Date.now() - this.startTime) / 1000 * 0.1) * 50 + 25;
      
      // Determine status
      if (this.state.intensity >= 0.9) {
        this.state.status = 'SUPERNOVA';
      } else if (this.state.intensity >= 0.7) {
        this.state.status = 'INFERNO';
      } else if (this.state.intensity >= 0.4) {
        this.state.status = 'BURNING';
      } else {
        this.state.status = 'IGNITING';
      }
      
      console.log(`\n🔥 INFERNO STATE:`);
      console.log(`   Status: ${this.state.status}`);
      console.log(`   Temperature: ${this.state.temperature.toFixed(1)} Hz`);
      console.log(`   Intensity: ${(this.state.intensity * 100).toFixed(1)}%`);
      
      // Trade decision: AGGRESSIVE mode - lower thresholds for FIRE
      const shouldTrade = state.coherence > (this.config.coherenceThreshold - 0.05) && 
                         voteCount >= Math.max(3, this.config.minConsensusVotes - 2); // More permissive
      
      if (shouldTrade) {
        const direction = state.Lambda > 0 ? 'BUY' : 'SELL';
        console.log(`\n🔥🔥🔥 FIRE TRADE: ${direction} 🔥🔥🔥`);
        
        if (!this.config.dryRun) {
          await this.executeTrade(direction as 'BUY' | 'SELL', price);
        } else {
          console.log(`[DRY RUN] Would ${direction} at $${price.toFixed(2)}`);
          this.trades.push({
            type: direction,
            price,
            size: this.config.tradeSize / price,
            timestamp: Date.now(),
            dryRun: true,
          });
        }
        
        this.state.totalTrades++;
      } else {
        console.log(`\n⏸️  HOLDING: Waiting for stronger signal`);
      }
      
      console.log('');
      
    } catch (error) {
      console.error('❌ CYCLE ERROR:', error);
    }
  }
  
  /**
   * EXECUTE TRADE
   */
  private async executeTrade(side: 'BUY' | 'SELL', price: number): Promise<void> {
    try {
      const quantity = (this.config.tradeSize / price).toFixed(6);
      
      console.log(`🔥 Executing ${side} order...`);
      console.log(`   Quantity: ${quantity} ETH`);
      console.log(`   Price: $${price.toFixed(2)}`);
      
      const order = await this.client.placeOrder({
        symbol: this.config.symbol,
        side,
        type: 'MARKET',
        quantity: parseFloat(quantity),
      });
      
      console.log(`✅ Order filled!`);
      console.log(`   Order ID: ${order.orderId}`);
      
      this.trades.push({
        type: side,
        price,
        size: parseFloat(quantity),
        timestamp: Date.now(),
        orderId: order.orderId,
      });
      
    } catch (error) {
      console.error('❌ Trade execution failed:', error);
    }
  }
  
  /**
   * SHOW INFERNO REPORT
   */
  private showInfernoReport(): void {
    console.log('\n\n');
    console.log('🔥'.repeat(70));
    console.log('INFERNO COMPLETE — FINAL REPORT');
    console.log('🔥'.repeat(70));
    console.log('');
    console.log(`🔥 INFERNO STATE:`);
    console.log(`   Status: ${this.state.status}`);
    console.log(`   Temperature: ${this.state.temperature.toFixed(1)} Hz`);
    console.log(`   Intensity: ${(this.state.intensity * 100).toFixed(1)}%`);
    console.log('');
    console.log(`📊 TRADING RESULTS:`);
    console.log(`   Total Trades: ${this.state.totalTrades}`);
    console.log(`   Buy Orders: ${this.trades.filter(t => t.type === 'BUY').length}`);
    console.log(`   Sell Orders: ${this.trades.filter(t => t.type === 'SELL').length}`);
    console.log('');
    console.log('🔥'.repeat(70));
    console.log('');
    console.log('Gary — you brought the smoke.');
    console.log('Gary — you lit the fire.');
    console.log('Gary — you BURNED THROUGH THE MARKET.');
    console.log('');
    console.log('The inferno is complete.');
    console.log('The system is blazing.');
    console.log('The dream is ROARING.');
    console.log('');
    console.log('🔥'.repeat(70));
    console.log('\n');
  }
  
  /**
   * SLEEP
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * CREATE INFERNO
 */
export const createInferno = (config: Partial<InfernoConfig> = {}, client: BinanceClient): Inferno => {
  const defaultConfig: InfernoConfig = {
    symbol: 'ETHUSDT',
    tradeSize: 10,
    coherenceThreshold: 0.90, // Lower than Co-Architect (more aggressive)
    consensusThreshold: 0.65, // Lower threshold (more permissive)
    minConsensusVotes: 4,     // Only need 4/9 votes (vs 6/9)
    cycleDelayMs: 3000,       // Faster cycles
    maxCycles: 30,
    dryRun: true,
  };
  
  return new Inferno({ ...defaultConfig, ...config }, client);
};
