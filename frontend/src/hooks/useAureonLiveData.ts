/**
 * 🌉 AUREON LIVE DATA HOOK 🌉
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Connects to the Python aureon_frontend_bridge.py WebSocket server
 * to receive LIVE data from ALL trading platforms and ALL systems.
 * 
 * DATA SOURCES:
 *   📊 Exchanges: Kraken, Binance, Alpaca, Capital.com
 *   🧠 Systems: V14, Mycelium Hub, Commando, Nexus, Multiverse, Miner, Omega
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { finiteOrNull } from '@/lib/reading';
import { bridgeWsUrl } from '@/config/serviceEndpoints';

// ════════════════════════════════════════════════════════════════════════════
// TYPES
// ════════════════════════════════════════════════════════════════════════════

export interface SystemSignal {
  system: string;
  signal_type: string;
  symbol: string;
  confidence: number;
  score: number;
  reason: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface ExchangeData {
  connected: boolean;
  total_value: number;
  balances: Record<string, number>;
  ticker_count: number;
  last_update: number;
  error: string | null;
}

export interface TopMover {
  symbol: string;
  exchange: string;
  change: number;
  price: number;
}

export interface BridgePayload {
  timestamp: number;
  exchanges: Record<string, ExchangeData>;
  total_portfolio_value: number;
  all_balances: Record<string, Record<string, number>>;
  signals: SystemSignal[];
  signal_count: number;
  systems_online: string[];
  systems_offline: string[];
  top_movers: TopMover[];
  opportunities: SystemSignal[];
}

export interface UseLiveDataResult {
  // Connection
  connected: boolean;
  connecting: boolean;
  error: string | null;
  
  // Exchange data
  exchanges: Record<string, ExchangeData>;
  totalPortfolioValue: number | null;
  allBalances: Record<string, Record<string, number>>;
  
  // Signals
  signals: SystemSignal[];
  signalCount: number;
  opportunities: SystemSignal[];
  
  // Systems
  systemsOnline: string[];
  systemsOffline: string[];
  
  // Market
  topMovers: TopMover[];
  
  // Actions
  refresh: () => void;
  reconnect: () => void;
  
  // Meta
  lastUpdate: number;
  updatesReceived: number;
}

// ════════════════════════════════════════════════════════════════════════════
// CONFIG
// ════════════════════════════════════════════════════════════════════════════

const BRIDGE_WS_URL = bridgeWsUrl;
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

// ════════════════════════════════════════════════════════════════════════════
// HOOK
// ════════════════════════════════════════════════════════════════════════════

export function useAureonLiveData(): UseLiveDataResult {
  // Connection state
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Data state
  const [exchanges, setExchanges] = useState<Record<string, ExchangeData>>({});
  const [totalPortfolioValue, setTotalPortfolioValue] = useState<number | null>(null);
  const [allBalances, setAllBalances] = useState<Record<string, Record<string, number>>>({});
  const [signals, setSignals] = useState<SystemSignal[]>([]);
  const [signalCount, setSignalCount] = useState(0);
  const [opportunities, setOpportunities] = useState<SystemSignal[]>([]);
  const [systemsOnline, setSystemsOnline] = useState<string[]>([]);
  const [systemsOffline, setSystemsOffline] = useState<string[]>([]);
  const [topMovers, setTopMovers] = useState<TopMover[]>([]);
  const [lastUpdate, setLastUpdate] = useState(0);
  const [updatesReceived, setUpdatesReceived] = useState(0);
  
  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  
  // Process incoming payload
  const processPayload = useCallback((payload: BridgePayload) => {
    setExchanges(payload.exchanges || {});
    setTotalPortfolioValue(finiteOrNull(payload.total_portfolio_value));
    setAllBalances(payload.all_balances || {});
    setSignals(payload.signals || []);
    setSignalCount(payload.signal_count || 0);
    setOpportunities(payload.opportunities || []);
    setSystemsOnline(payload.systems_online || []);
    setSystemsOffline(payload.systems_offline || []);
    setTopMovers(payload.top_movers || []);
    setLastUpdate(payload.timestamp || Date.now() / 1000);
    setUpdatesReceived(prev => prev + 1);
  }, []);
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    setConnecting(true);
    setError(null);
    
    try {
      console.log(`🌉 Connecting to Aureon Bridge: ${BRIDGE_WS_URL}`);
      wsRef.current = new WebSocket(BRIDGE_WS_URL);
      
      wsRef.current.onopen = () => {
        console.log('🌉 Aureon Bridge: CONNECTED');
        setConnected(true);
        setConnecting(false);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle different message types
          switch (message.type) {
            case 'initial_state':
            case 'stream_tick':
            case 'refresh':
              processPayload(message.payload);
              break;
              
            case 'signals':
              setSignals(message.payload || []);
              break;
              
            default:
              console.log('🌉 Unknown message type:', message.type);
          }
        } catch (err) {
          console.error('🌉 Parse error:', err);
        }
      };
      
      wsRef.current.onerror = (event) => {
        console.error('🌉 WebSocket error:', event);
        setError('Connection error');
      };
      
      wsRef.current.onclose = (event) => {
        console.log(`🌉 WebSocket closed: ${event.code} ${event.reason}`);
        setConnected(false);
        setConnecting(false);
        
        // Auto-reconnect
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++;
          const delay = RECONNECT_DELAY * Math.min(reconnectAttemptsRef.current, 5);
          console.log(`🌉 Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
          
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        } else {
          setError('Max reconnection attempts reached');
        }
      };
      
    } catch (err) {
      console.error('🌉 Connection error:', err);
      setError(err instanceof Error ? err.message : 'Connection failed');
      setConnecting(false);
    }
  }, [processPayload]);
  
  // Refresh - request new data
  const refresh = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'refresh' }));
    }
  }, []);
  
  // Reconnect
  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);
  
  // Connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);
  
  return {
    // Connection
    connected,
    connecting,
    error,
    
    // Exchange data
    exchanges,
    totalPortfolioValue,
    allBalances,
    
    // Signals
    signals,
    signalCount,
    opportunities,
    
    // Systems
    systemsOnline,
    systemsOffline,
    
    // Market
    topMovers,
    
    // Actions
    refresh,
    reconnect,
    
    // Meta
    lastUpdate,
    updatesReceived,
  };
}

export default useAureonLiveData;
