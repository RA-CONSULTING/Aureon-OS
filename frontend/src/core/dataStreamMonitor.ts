// Data Stream Monitor - Tracks all API request/response status
// Shows which data streams are active, latency, success/failure rates

export interface StreamEntry {
  id: string;
  endpoint: string;
  direction: 'IN' | 'OUT';
  status: 'success' | 'error' | 'pending';
  timestamp: Date;
  latencyMs: number;
  bytesSent?: number;
  bytesReceived?: number;
  errorMessage?: string;
  requestBody?: any;
  responseBody?: any;
}

export interface StreamStats {
  endpoint: string;
  successCount: number;
  errorCount: number;
  avgLatencyMs: number;
  lastSuccess: Date | null;
  lastError: Date | null;
  isHealthy: boolean;
}

export interface DataStreamMonitorState {
  streams: StreamEntry[];
  stats: Map<string, StreamStats>;
  totalRequests: number;
  totalErrors: number;
  overallHealth: 'healthy' | 'degraded' | 'down';
  lastUpdate: Date;
}

type StreamListener = (state: DataStreamMonitorState) => void;

class DataStreamMonitorClass {
  private streams: StreamEntry[] = [];
  private stats: Map<string, StreamStats> = new Map();
  private listeners: Set<StreamListener> = new Set();
  private maxEntries = 100;
  private healthThresholdMs = 30000; // 30s without success = unhealthy

  constructor() {
    // Initialize with known endpoints
    const knownEndpoints = [
      'ingest-master-equation',
      'ingest-omega-equation',
      'ingest-prism-state',
      'ingest-rainbow-bridge',
      'ingest-decision-fusion',
      'ingest-ftcp-detector',
      'ingest-qgita-signal',
      'ingest-hnc-detection',
      'ingest-eckoushic-cascade',
      'ingest-harmonic-6d',
      'ingest-unity-event',
      'ingest-akashic-attunement',
      'ingest-stargate-harmonizer',
      'ingest-stargate-network',
      'ingest-probability-matrix',
      'ingest-risk-manager',
      'ingest-performance-tracker',
      'ingest-planetary-modulation',
      'ingest-integral-aqal',
      'ingest-elephant-memory',
      'get-user-market-data',
      'get-user-balances',
      'execute-trade',
      'fetch-binance-market-data',
    ];
    
    knownEndpoints.forEach(ep => {
      this.stats.set(ep, {
        endpoint: ep,
        successCount: 0,
        errorCount: 0,
        avgLatencyMs: 0,
        lastSuccess: null,
        lastError: null,
        isHealthy: false,
      });
    });
  }

  // Record an outgoing request (OUT)
  recordRequest(endpoint: string, requestBody?: any): string {
    const id = `${endpoint}-${Date.now()}-${crypto.randomUUID()}`;
    
    const entry: StreamEntry = {
      id,
      endpoint: this.extractEndpoint(endpoint),
      direction: 'OUT',
      status: 'pending',
      timestamp: new Date(),
      latencyMs: 0,
      bytesSent: requestBody ? JSON.stringify(requestBody).length : 0,
      requestBody,
    };
    
    this.addEntry(entry);
    return id;
  }

  // Record a response (IN)
  recordResponse(id: string, success: boolean, responseBody?: any, errorMessage?: string) {
    const entry = this.streams.find(s => s.id === id);
    if (entry) {
      entry.direction = 'IN';
      entry.status = success ? 'success' : 'error';
      entry.latencyMs = Date.now() - entry.timestamp.getTime();
      entry.bytesReceived = responseBody ? JSON.stringify(responseBody).length : 0;
      entry.responseBody = responseBody;
      entry.errorMessage = errorMessage;
      
      this.updateStats(entry);
      this.notifyListeners();
    }
  }

  // Simplified: record complete request/response cycle
  recordStream(endpoint: string, success: boolean, latencyMs: number, requestBody?: any, responseBody?: any, errorMessage?: string) {
    const cleanEndpoint = this.extractEndpoint(endpoint);
    
    const entry: StreamEntry = {
      id: `${cleanEndpoint}-${Date.now()}`,
      endpoint: cleanEndpoint,
      direction: success ? 'IN' : 'OUT',
      status: success ? 'success' : 'error',
      timestamp: new Date(),
      latencyMs,
      bytesSent: requestBody ? JSON.stringify(requestBody).length : 0,
      bytesReceived: responseBody ? JSON.stringify(responseBody).length : 0,
      requestBody,
      responseBody,
      errorMessage,
    };
    
    this.addEntry(entry);
    this.updateStats(entry);
  }

  private extractEndpoint(url: string): string {
    // Extract function name from full URL
    const match = url.match(/functions\/v1\/([^?]+)/);
    if (match) return match[1];
    
    // Or just return the last part of the path
    const parts = url.split('/');
    return parts[parts.length - 1].split('?')[0] || url;
  }

  private addEntry(entry: StreamEntry) {
    this.streams.unshift(entry);
    if (this.streams.length > this.maxEntries) {
      this.streams = this.streams.slice(0, this.maxEntries);
    }
    this.notifyListeners();
  }

  private updateStats(entry: StreamEntry) {
    let stat = this.stats.get(entry.endpoint);
    
    if (!stat) {
      stat = {
        endpoint: entry.endpoint,
        successCount: 0,
        errorCount: 0,
        avgLatencyMs: 0,
        lastSuccess: null,
        lastError: null,
        isHealthy: false,
      };
      this.stats.set(entry.endpoint, stat);
    }
    
    if (entry.status === 'success') {
      stat.successCount++;
      stat.lastSuccess = entry.timestamp;
      // Running average
      stat.avgLatencyMs = (stat.avgLatencyMs * (stat.successCount - 1) + entry.latencyMs) / stat.successCount;
    } else if (entry.status === 'error') {
      stat.errorCount++;
      stat.lastError = entry.timestamp;
    }
    
    // Check health - healthy if last success within threshold
    stat.isHealthy = stat.lastSuccess !== null && 
      (Date.now() - stat.lastSuccess.getTime()) < this.healthThresholdMs;
  }

  subscribe(listener: StreamListener): () => void {
    this.listeners.add(listener);
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  private notifyListeners() {
    const state = this.getState();
    this.listeners.forEach(l => l(state));
  }

  getState(): DataStreamMonitorState {
    const totalRequests = Array.from(this.stats.values()).reduce((sum, s) => sum + s.successCount + s.errorCount, 0);
    const totalErrors = Array.from(this.stats.values()).reduce((sum, s) => sum + s.errorCount, 0);
    const healthyCount = Array.from(this.stats.values()).filter(s => s.isHealthy).length;
    const totalEndpoints = this.stats.size;
    
    let overallHealth: 'healthy' | 'degraded' | 'down' = 'healthy';
    if (healthyCount === 0) overallHealth = 'down';
    else if (healthyCount < totalEndpoints * 0.5) overallHealth = 'degraded';
    
    return {
      streams: [...this.streams],
      stats: new Map(this.stats),
      totalRequests,
      totalErrors,
      overallHealth,
      lastUpdate: new Date(),
    };
  }

  getStreamsByEndpoint(endpoint: string): StreamEntry[] {
    return this.streams.filter(s => s.endpoint === endpoint);
  }

  getHealthyEndpoints(): string[] {
    return Array.from(this.stats.values())
      .filter(s => s.isHealthy)
      .map(s => s.endpoint);
  }

  getUnhealthyEndpoints(): string[] {
    return Array.from(this.stats.values())
      .filter(s => !s.isHealthy && (s.successCount > 0 || s.errorCount > 0))
      .map(s => s.endpoint);
  }

  clearHistory() {
    this.streams = [];
    this.stats.forEach(stat => {
      stat.successCount = 0;
      stat.errorCount = 0;
      stat.avgLatencyMs = 0;
      stat.lastSuccess = null;
      stat.lastError = null;
      stat.isHealthy = false;
    });
    this.notifyListeners();
  }
}

export const dataStreamMonitor = new DataStreamMonitorClass();
