import React, { useEffect, useState, useCallback } from 'react';
import {
  OrcaStatus,
  CoordinationState,
  FeedsStatus,
  DecisionsResponse,
  UnifiedState,
  SystemHealth,
} from '../types';

/**
 *  UNIFIED ORCA COMMAND DASHBOARD
 *
 * Central command center for monitoring and controlling the Orca kill cycle
 * with real-time system coordination, feed status, and trading decisions.
 */

interface DashboardState {
  orcaStatus: OrcaStatus | null;
  coordinationState: CoordinationState | null;
  feedsStatus: FeedsStatus | null;
  decisions: DecisionsResponse | null;
  systemHealth: SystemHealth | null;
  loading: boolean;
  error: string | null;
  lastUpdate: number;
}

const UnifiedOrcaCommandDashboard: React.FC = () => {
  const [state, setState] = useState<DashboardState>({
    orcaStatus: null,
    coordinationState: null,
    feedsStatus: null,
    decisions: null,
    systemHealth: null,
    loading: true,
    error: null,
    lastUpdate: 0,
  });

  const API_BASE = 'http://localhost:13334/api';

  // Fetch all unified state
  const fetchUnifiedState = useCallback(async () => {
    try {
      const [orca, coordination, feeds, decisions, health] = await Promise.all([
        fetch(`${API_BASE}/orca-status`).then(r => r.json()),
        fetch(`${API_BASE}/system-coordination`).then(r => r.json()),
        fetch(`${API_BASE}/feed-status`).then(r => r.json()),
        fetch(`${API_BASE}/decisions`).then(r => r.json()),
        fetch(`${API_BASE}/system-health`).then(r => r.json()),
      ]);

      setState(prev => ({
        ...prev,
        orcaStatus: orca,
        coordinationState: coordination,
        feedsStatus: feeds,
        decisions,
        systemHealth: health,
        loading: false,
        error: null,
        lastUpdate: Date.now(),
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Unknown error',
        loading: false,
      }));
    }
  }, []);

  // Auto-refresh every 1 second
  useEffect(() => {
    fetchUnifiedState();
    const interval = setInterval(fetchUnifiedState, 1000);
    return () => clearInterval(interval);
  }, [fetchUnifiedState]);

  const sendOrcaCommand = async (command: string) => {
    try {
      const response = await fetch(`${API_BASE}/orca-command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, parameters: {} }),
      });
      const result = await response.json();
      alert(`Command "${command}" sent: ${result.message}`);
      fetchUnifiedState();
    } catch (err) {
      alert(`Error sending command: ${err}`);
    }
  };

  if (state.loading && !state.orcaStatus) {
    return (
      <div className="flex items-center justify-center h-screen bg-card text-foreground">
        <div className="text-center">
          <p className="text-muted-foreground">Loading Unified Dashboard…</p>
        </div>
      </div>
    );
  }

  const orcaReady = state.orcaStatus?.ready_for_execution ?? false;
  const allSystemsHealthy = (state.systemHealth?.healthy ?? 0) === (state.systemHealth?.total ?? 1);
  const feedsHealthy = Object.values(state.feedsStatus || {}).every(f => f.is_healthy);

  return (
    <div className="bg-background text-foreground p-4">
      {/* Header */}
      <div className="mb-6 border-b border-border pb-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight mb-2">Aureon Unified Dashboard</h1>
            <p className="text-muted-foreground">
              Real-time Orca Kill Cycle Control & System Coordination
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">
              Updated: {new Date(state.lastUpdate).toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>

      {state.error && (
        <div className="bg-destructive border border-destructive rounded p-4 mb-4">
          <p className="text-destructive">Error: {state.error}</p>
        </div>
      )}

      {/* Top Status Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatusCard
          title="Orca Status"
          status={state.orcaStatus?.status || 'unknown'}
          ready={orcaReady}
          details={`${state.orcaStatus?.blockers?.length || 0} blockers`}
        />
        <StatusCard
          title="System Coordination"
          status={state.coordinationState?.orca_ready ? 'Ready' : 'Not Ready'}
          ready={state.coordinationState?.orca_ready || false}
          details={`${state.systemHealth?.healthy || 0}/${state.systemHealth?.total || 0} systems`}
        />
        <StatusCard
          title="Feeds"
          status={feedsHealthy ? 'Healthy' : 'Degraded'}
          ready={feedsHealthy}
          details={`${Object.values(state.feedsStatus || {}).reduce((sum, f) => sum + f.event_count, 0)} events`}
        />
        <StatusCard
          title="Overall"
          status={orcaReady && allSystemsHealthy ? 'Ready' : 'Standby'}
          ready={orcaReady && allSystemsHealthy}
          details={orcaReady && allSystemsHealthy ? 'All systems go' : 'Awaiting conditions'}
        />
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Left Panel: Orca Control */}
        <div className="col-span-1 bg-card rounded border border-border p-4">
          <h2 className="text-lg font-semibold mb-4 text-warning">Orca Kill Cycle</h2>

          <div className="space-y-3">
            <div className="bg-muted rounded p-3">
              <p className="text-muted-foreground text-sm">Status</p>
              <p className="text-lg font-mono">
                {state.orcaStatus?.status || 'unknown'}
              </p>
            </div>

            <div className="bg-muted rounded p-3">
              <p className="text-muted-foreground text-sm">Ready for Execution</p>
              <p className={`text-lg font-bold ${orcaReady ? 'text-success' : 'text-destructive'}`}>
                {orcaReady ? 'Yes' : 'No'}
              </p>
            </div>

            {state.orcaStatus?.blockers && state.orcaStatus.blockers.length > 0 && (
              <div className="bg-destructive rounded p-3 text-sm">
                <p className="text-destructive font-bold mb-2">Blockers:</p>
                <ul className="text-destructive">
                  {state.orcaStatus.blockers.map((b, i) => (
                    <li key={i}>• {b}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 pt-4">
              <button
                onClick={() => sendOrcaCommand('start')}
                disabled={!orcaReady}
                className={`py-2 px-3 rounded font-bold text-sm ${
                  orcaReady
                    ? 'bg-success hover:bg-success'
                    : 'bg-muted cursor-not-allowed'
                }`}
              >
                Start
              </button>
              <button
                onClick={() => sendOrcaCommand('stop')}
                className="py-2 px-3 rounded font-bold text-sm bg-destructive hover:bg-destructive"
              >
                Stop
              </button>
              <button
                onClick={() => sendOrcaCommand('pause')}
                className="py-2 px-3 rounded font-bold text-sm bg-warning hover:bg-warning"
              >
                Pause
              </button>
              <button
                onClick={() => fetchUnifiedState()}
                className="py-2 px-3 rounded font-bold text-sm bg-primary hover:bg-primary"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Center Panel: Decisions Log */}
        <div className="col-span-1 bg-card rounded border border-border p-4">
          <h2 className="text-lg font-semibold mb-4 text-primary">Recent Decisions</h2>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {state.decisions?.decisions && Object.entries(state.decisions.decisions).length > 0 ? (
              Object.entries(state.decisions.decisions).map(([symbol, decision]) => (
                <div key={symbol} className="bg-muted rounded p-3 text-sm">
                  <div className="flex justify-between items-start mb-1">
                    <p className="font-bold text-foreground">{symbol}</p>
                    <span
                      className={`px-2 py-1 rounded text-xs font-bold ${
                        decision.type === 'buy'
                          ? 'bg-success text-success'
                          : decision.type === 'sell'
                          ? 'bg-destructive text-destructive'
                          : 'bg-muted text-foreground'
                      }`}
                    >
                      {decision.type.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-muted-foreground">
                    Confidence: {(decision.confidence * 100).toFixed(0)}%
                  </p>
                  <p className="text-muted-foreground text-xs">
                    {decision.reason}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground text-center py-8">No decisions yet</p>
            )}
          </div>
        </div>

        {/* Right Panel: Feeds & Risk */}
        <div className="col-span-1 bg-card rounded border border-border p-4">
          <h2 className="text-lg font-semibold mb-4 text-success">Feed Status</h2>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {state.feedsStatus ? (
              Object.entries(state.feedsStatus).map(([name, feed]) => (
                <div key={name} className="bg-muted rounded p-3">
                  <div className="flex justify-between items-center mb-1">
                    <p className="font-mono text-sm">{name}</p>
                    <span
                      className={`w-2 h-2 rounded-full ${feed.is_healthy ? 'bg-success' : 'bg-destructive'}`}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {feed.event_count} events
                  </p>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground">Loading feed status...</p>
            )}
          </div>
        </div>
      </div>

      {/* System Coordination Panel */}
      <div className="bg-card rounded border border-border p-4">
        <h2 className="text-lg font-semibold mb-4 text-primary">System Coordination</h2>

        {state.coordinationState && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-muted rounded p-3">
              <p className="text-muted-foreground text-sm">Total Systems</p>
              <p className="text-3xl font-bold text-foreground">
                {state.coordinationState.total_systems}
              </p>
            </div>

            <div className="bg-muted rounded p-3">
              <p className="text-muted-foreground text-sm">System States</p>
              <div className="text-sm font-mono space-y-1">
                {Object.entries(state.coordinationState.state_counts).map(([state, count]) => (
                  <p key={state}>
                    {state}: <span className="font-bold">{count}</span>
                  </p>
                ))}
              </div>
            </div>

            <div className="bg-muted rounded p-3">
              <p className="text-muted-foreground text-sm">Orca Dependencies</p>
              <div className="text-sm space-y-1">
                {state.coordinationState.orca_dependencies.required.map(dep => (
                  <p key={dep} className="font-mono text-xs text-muted-foreground">
                    ✓ {dep}
                  </p>
                ))}
              </div>
            </div>

            <div className="bg-muted rounded p-3">
              <p className="text-muted-foreground text-sm">Health</p>
              <p className={`text-2xl font-bold ${state.systemHealth?.health_percentage === 100 ? 'text-success' : 'text-warning'}`}>
                {state.systemHealth?.health_percentage.toFixed(0)}%
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Status Card Component
 */
interface StatusCardProps {
  title: string;
  status: string;
  ready: boolean;
  details: string;
}

const StatusCard: React.FC<StatusCardProps> = ({ title, status, ready, details }) => {
  return (
    <div className={`rounded border p-4 ${ready ? 'bg-success border-success' : 'bg-muted border-border'}`}>
      <p className="text-muted-foreground text-sm mb-2">{title}</p>
      <p className={`text-xl font-bold mb-2 ${ready ? 'text-success' : 'text-muted-foreground'}`}>
        {status}
      </p>
      <p className="text-xs text-muted-foreground">{details}</p>
    </div>
  );
};

export default UnifiedOrcaCommandDashboard;
