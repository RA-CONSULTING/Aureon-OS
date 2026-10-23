
import { BinanceClient } from '../core/binanceClient';
import * as dotenv from 'dotenv';

// No dotenv.config() here, we rely on passed env vars or we manually load if needed
// But for this script, we'll just use the args or env vars passed to it

async function main() {
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  
  if (!apiKey || !apiSecret) {
    console.error('❌ API credentials required!');
    process.exit(1);
  }
  
  const client = new BinanceClient({ apiKey, apiSecret });
  
  try {
    const account = await client.getAccount();
    const balances = account.balances.filter(b => parseFloat(b.free) > 0 || parseFloat(b.locked) > 0);
    
    console.log('\n💰 QUACKERS 2 ASSETS REPORT 💰\n');
    
    let totalUsd = 0;
    
    for (const b of balances) {
      const free = parseFloat(b.free);
      const locked = parseFloat(b.locked);
      const total = free + locked;
      
      if (total > 0) {
        let price = 1;
        if (b.asset !== 'USDT' && b.asset !== 'USDC' && b.asset !== 'LDUSDC') {
            try {
                price = await client.getPrice(`${b.asset}USDT`);
            } catch (e) {
                try {
                    price = await client.getPrice(`${b.asset}USDC`);
                } catch (e2) {
                    price = 0;
                }
            }
        }
        
        const value = total * price;
        totalUsd += value;
        
        if (value > 0.01) {
            console.log(`   ${b.asset.padEnd(8)}: ${total.toFixed(8)} ($${value.toFixed(2)})`);
        }
      }
    }
    
    console.log('\n' + '─'.repeat(30));
    console.log(`💵 TOTAL ESTIMATED VALUE: $${totalUsd.toFixed(2)}`);
    console.log('─'.repeat(30) + '\n');
    
  } catch (error: any) {
    console.error('Error:', error.message);
  }
}

main();
