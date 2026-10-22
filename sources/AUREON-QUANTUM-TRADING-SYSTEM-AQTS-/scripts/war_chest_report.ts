import { BinanceClient } from '../core/binanceClient';
import { loadAccountsFromJson, AccountRecord } from './utils/accountLoader';

async function getAccountBalance(account: AccountRecord): Promise<number> {
    const client = new BinanceClient({ apiKey: account.apiKey, apiSecret: account.apiSecret });
    try {
        const acc = await client.getAccount();
        const balances = acc.balances.filter((b: any) => parseFloat(b.free) > 0 || parseFloat(b.locked) > 0);
        
        let totalUsd = 0;
        
        for (const b of balances) {
            const free = parseFloat(b.free);
            const locked = parseFloat(b.locked);
            const total = free + locked;
            
            if (total > 0) {
                let price = 0;
                if (b.asset === 'USDT' || b.asset === 'USDC' || b.asset === 'BUSD' || b.asset === 'FDUSD') {
                    price = 1;
                } else {
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
                totalUsd += total * price;
            }
        }
        return totalUsd;
    } catch (e: any) {
        const label = account.name || 'Quacker';
        console.log(`   ❌ ${label}: Error fetching balance - ${e.message}`);
        return 0;
    }
}

async function main() {
    console.log('\n' + '💰'.repeat(60));
    console.log('  🦁 GENERAL QUACKERS: WAR CHEST INSPECTION 🦁');
    console.log('💰'.repeat(60) + '\n');

    const accounts = loadAccountsFromJson();
    
    if (accounts.length === 0) {
        console.log('❌ No accounts found.');
        return;
    }

    let grandTotal = 0;
    
    console.log(`🔍 Inspecting ${accounts.length} Wallets...\n`);

    accounts.forEach((account, idx) => account.name ||= `Quacker-${idx + 1}`);

    for (const [idx, account] of accounts.entries()) {
        const balance = await getAccountBalance(account);
        grandTotal += balance;
        const label = account.name || `Quacker-${idx + 1}`;
        console.log(`   🦆 ${label}: $${balance.toFixed(2)}`);
    }

    console.log('\n' + '─'.repeat(40));
    console.log(`💵 TOTAL WAR CHEST: $${grandTotal.toFixed(2)}`);
    console.log('─'.repeat(40) + '\n');
}

main();
