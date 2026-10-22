#!/usr/bin/env node
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { BinanceClient } from '../core/binanceClient';

const app = express();
app.use(cors());
app.use(express.json());

const PORT = Number(process.env.STATUS_PORT || 8787);
const LOG_DIR = path.resolve(process.cwd(), 'logs');
const MOCK = String(process.env.STATUS_MOCK || '').toLowerCase() === 'true';

function readTail(file: string, lines = 10): string[] {
  try {
    const p = path.join(LOG_DIR, file);
    if (!fs.existsSync(p)) return [];
    const content = fs.readFileSync(p, 'utf-8');
    const arr = content.split(/\r?\n/).filter(Boolean);
    return arr.slice(-lines);
  } catch {
    return [];
  }
}

function getClient() {
  const apiKey = process.env.BINANCE_API_KEY;
  const apiSecret = process.env.BINANCE_API_SECRET;
  if (!apiKey || !apiSecret) throw new Error('Missing BINANCE_API_KEY/SECRET');
  return new BinanceClient({ apiKey, apiSecret, testnet: !(process.env.AUREON_FUSION_ARM_LIVE === "1" && process.env.BINANCE_TESTNET === "false") });
}

app.get('/api/status', async (_req, res) => {
  try {
    if (MOCK) {
      const px = 3000 + Math.random() * 500;
      const eth = 0.002;
      const usdt = 0;
      return res.json({ eth, usdt, ethUsdt: px, totalUsd: usdt + eth * px, canTrade: true, mock: true });
    }
    const client = getClient();
    const acct = await client.getAccount();
    const eth = Number(acct.balances.find(b=>b.asset==='ETH')?.free || 0);
    const usdt = Number(acct.balances.find(b=>b.asset==='USDT')?.free || 0);
    const px = await client.getPrice('ETHUSDT');
    res.json({ eth, usdt, ethUsdt: px, totalUsd: usdt + eth*px, canTrade: acct.canTrade });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/bots', (_req, res) => {
  const bots = [
    { name: 'Hummingbird', log: 'hummingbird.log' },
    { name: 'ArmyAnts', log: 'armyAnts.log' },
    { name: 'LoneWolf', log: 'loneWolf.log' },
    { name: 'BalanceWatcher', log: 'balanceWatcher.log' },
  ];
  const data = bots.map(b => ({ name: b.name, tail: readTail(b.log, 8) }));
  res.json({ bots: data });
});

app.get('/api/trades', async (req, res) => {
  try {
    const symbols = String(req.query.symbols || 'ETHUSDT,BTCUSDT,BNBUSDT,SOLUSDT,ADAUSDT').split(',').map(s=>s.trim().toUpperCase());
    if (MOCK) {
      const now = Date.now();
      const trades: Record<string, any[]> = Object.fromEntries(symbols.map(s => [s, [
        { id: 1, symbol: s, qty: '1.0', price: '100.0', time: now - 60000 },
        { id: 2, symbol: s, qty: '0.5', price: '101.0', time: now - 30000 },
      ]]));
      return res.json({ trades, mock: true });
    }
    const client = getClient();
    const out: Record<string, any[]> = {};
    for (const sym of symbols) {
      try {
        const t = await client.getMyTrades(sym, 10);
        out[sym] = t;
      } catch {
        out[sym] = [];
      }
    }
    res.json({ trades: out });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(PORT, () => {
  console.log(`Status server listening on http://localhost:${PORT}`);
});
