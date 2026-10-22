#!/usr/bin/env npx tsx
import { BinanceClient } from '../core/binanceClient';
import * as dotenv from 'dotenv';

dotenv.config();

const apiKey = process.env.BINANCE_API_KEY || 'rnGhYpDT4gFIRu9Y6RdH4p43LdEvtcdPAhxdlX3k32E1QbFo8W2qNS3P1xO2FxfW';
const apiSecret = process.env.BINANCE_API_SECRET || 'ylIreJLGRCV5IWYNhiM0w6vFyvFzh4IOqwV1K4pErSdss4p1uR4BIdXw9JJNKOQJ';
const testnet = !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false");

async function checkBalances() {
  const client = new BinanceClient({ apiKey, apiSecret, testnet });
  
  try {
    const account = await client.getAccount();
    const balances = account.balances.filter(b => parseFloat(b.free) > 0 || parseFloat(b.locked) > 0);
    
    console.log('\n💰 QUACKERS 4 - CURRENT ASSETS REPORT 💰\n');
    
    let totalValue = 0;
    for (const balance of balances) {
      const free = parseFloat(balance.free);
      const locked = parseFloat(balance.locked);
      const total = free + locked;
      
      if (total > 0.00001) {
        let usdValue = total;
        
        // Try to get USD value for non-stablecoin assets
        if (!['USDT', 'USDC', 'BUSD', 'FDUSD'].includes(balance.asset)) {
          try {
            const priceSymbol = `${balance.asset}USDC`;
            const price = await client.getPrice(priceSymbol);
            usdValue = total * price;
          } catch {
            // If no USDC pair, assume it's close to 0 or use the value as-is
          }
        }
        
        totalValue += usdValue;
        console.log(`   ${balance.asset.padEnd(8)}: ${total.toFixed(8)} ($${usdValue.toFixed(2)})`);
      }
    }
    
    console.log('\n' + '─'.repeat(30));
    console.log(`💵 TOTAL ESTIMATED VALUE: $${totalValue.toFixed(2)}`);
    console.log('─'.repeat(30) + '\n');
    
  } catch (error: any) {
    console.error('❌', error.message);
  }
}

checkBalances();
