/**
 * Environment configuration for AUREON trading system
 * Supports both development and production modes with proper isolation
 */

import dotenv from 'dotenv';

// Load .env file if it exists
dotenv.config();

export interface EnvironmentConfig {
  mode: 'development' | 'testnet' | 'production';
  binance: {
    apiKey: string | null;
    apiSecret: string | null;
    testnet: boolean;
  };
  logging: {
    level: 'debug' | 'info' | 'warn' | 'error';
    verbose: boolean;
  };
  trading: {
    paperMode: boolean;
    maxOrderSize: number;
    maxDailyTrades: number;
    riskLimitPercent: number;
  };
}

function getEnvironmentConfig(): EnvironmentConfig {
  const mode = (process.env.NODE_ENV || 'development') as 'development' | 'testnet' | 'production';
  const binanceApiKey = process.env.BINANCE_API_KEY || null;
  const binanceApiSecret = process.env.BINANCE_API_SECRET || null;
  const binanceTestnet = process.env.BINANCE_TESTNET !== 'false'; // default to testnet for safety
  
  const loggingLevel = (process.env.LOG_LEVEL || 'info') as 'debug' | 'info' | 'warn' | 'error';
  const verboseLogging = process.env.VERBOSE_LOGGING === 'true';

  const paperMode = process.env.PAPER_MODE !== 'false'; // default to paper mode
  const maxOrderSize = Number(process.env.MAX_ORDER_SIZE || 10000);
  const maxDailyTrades = Number(process.env.MAX_DAILY_TRADES || 1000);
  const riskLimitPercent = Number(process.env.RISK_LIMIT_PERCENT || 2);

  return {
    mode,
    binance: {
      apiKey: binanceApiKey,
      apiSecret: binanceApiSecret,
      testnet: binanceTestnet,
    },
    logging: {
      level: loggingLevel,
      verbose: verboseLogging,
    },
    trading: {
      paperMode,
      maxOrderSize,
      maxDailyTrades,
      riskLimitPercent,
    },
  };
}

export const envConfig = getEnvironmentConfig();

// Logging utility
export function log(level: 'debug' | 'info' | 'warn' | 'error', message: string, data?: any) {
  const levelPriority = { debug: 0, info: 1, warn: 2, error: 3 };
  if (levelPriority[level] >= levelPriority[envConfig.logging.level]) {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
    console.log(prefix, message, data ? JSON.stringify(data, null, 2) : '');
  }
}
