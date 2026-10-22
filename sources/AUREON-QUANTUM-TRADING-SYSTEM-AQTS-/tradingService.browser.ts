import { MonitoringEvent } from './types';

export type TradeSide = 'BUY' | 'SELL';

// Simple base64 encoding for API secret (note: not cryptographically secure)
const encryptApiSecret = async (secret: string, _key: string): Promise<string> => {
  return btoa(secret);
};

const decryptApiSecret = async (encrypted: string, _key: string): Promise<string> => {
  return atob(encrypted);
};

export interface StoredCredentials {
  apiKey: string;
  apiSecret: string;
  mode: 'live' | 'testnet';
}

export interface TradeRequest {
  pair: string;
  side: TradeSide;
  quantity: number;
  mode?: 'live' | 'testnet';
}

export interface TradeExecutionResult {
  success: boolean;
  message: string;
  orderId?: string | number;
  response?: unknown;
  errorCode?: number;
}

export const getStoredCredentials = async (apiKeyOptional?: string): Promise<StoredCredentials | null> => {
  if (typeof window === 'undefined') return null;
  const apiKey = window.localStorage.getItem('aureon_api_key') || apiKeyOptional || '';
  const encApiSecret = window.localStorage.getItem('aureon_api_secret') || '';
  const mode = (window.localStorage.getItem('aureon_api_mode') as 'live' | 'testnet') || 'testnet';
  if (!apiKey || !encApiSecret) return null;
  const apiSecret = await decryptApiSecret(encApiSecret, apiKey);
  return { apiKey, apiSecret, mode };
};

export const storeCredentials = async (c: StoredCredentials): Promise<void> => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem('aureon_api_key', c.apiKey);
  window.localStorage.setItem('aureon_api_secret', await encryptApiSecret(c.apiSecret, c.apiKey));
  window.localStorage.setItem('aureon_api_mode', c.mode);
};

export const clearStoredCredentials = (): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem('aureon_api_key');
  window.localStorage.removeItem('aureon_api_secret');
  window.localStorage.removeItem('aureon_api_mode');
};

export const executeMarketTrade = async (_req: TradeRequest): Promise<TradeExecutionResult> => ({
  success: false,
  message: 'Execution disabled in this environment',
});

export const annotateTradeEventWithExecution = (event: MonitoringEvent, exec: TradeExecutionResult): MonitoringEvent => ({
  ...event,
  executionStatus: exec.success ? 'FILLED' : 'FAILED',
  executionMessage: exec.message,
  orderId: exec.orderId,
});
