import { useQuantumWarRoom } from '@/hooks/useQuantumWarRoom';
import { useGlobalState } from '@/hooks/useGlobalState';
import { useMultiExchangeBalances } from '@/hooks/useMultiExchangeBalances';
import { useHncCoherence } from '@/hooks/useHncCoherence';
import { QuantumStatePanel } from './warroom/QuantumStatePanel';
import { HistoricalTimeline } from './warroom/HistoricalTimeline';
import { LiveStrikeStream } from './warroom/LiveStrikeStream';
import { AurisNodesOrbit } from './warroom/AurisNodesOrbit';
import { ProjectionHorizon } from './warroom/ProjectionHorizon';
import { GasTankDisplay } from './warroom/GasTankDisplay';
import { UnifiedBusStatus } from './warroom/UnifiedBusStatus';
import { MultiExchangePanel } from './warroom/MultiExchangePanel';
import { SystemHealthPanel } from './SystemHealthPanel';
import { PrimeSealStatusPanel } from './warroom/PrimeSealStatusPanel';
import { PrismFrequencyPanel } from './warroom/PrismFrequencyPanel';
import { ProbabilityFusionPanel } from './warroom/ProbabilityFusionPanel';
import { TemporalLadderStatus } from './warroom/TemporalLadderStatus';
import { FullEcosystemStatus } from './warroom/FullEcosystemStatus';
import { TradeControlsHeader } from './warroom/TradeControlsHeader';
import { CredentialStatusPanel } from './warroom/CredentialStatusPanel';
import { ActivePositionsPanel } from './warroom/ActivePositionsPanel';
import { TradingReadinessCheck } from './warroom/TradingReadinessCheck';
import { TradingStatusPanel } from './warroom/TradingStatusPanel';
import { LiveTradeStream } from './warroom/LiveTradeStream';
import { LaunchButton } from './warroom/LaunchButton';
import { Badge } from '@/components/ui/badge';
// Exchange scouts + signal leaderboard
import { SniperLeaderboard } from './warroom/SniperLeaderboard';
import { DuckCommandoIntel } from './warroom/DuckCommandoIntel';

export default function WarRoomDashboard() {
  const { state, launchAssault, emergencyStop } = useQuantumWarRoom();
  const globalState = useGlobalState();
  const { exchangeStatuses: liveExchanges } = useMultiExchangeBalances();
  // REAL HNC coherence Γ from the operator (/api/pulse), not a simulation.
  const { gamma: hncGamma } = useHncCoherence();

  // Scout intel = REAL per-exchange connection state from get-user-balances.
  // Kill/PnL telemetry is intentionally omitted (no real kill-tracking source in the
  // frontend yet) so the panel shows genuine connection dots, never fabricated stats.
  const exchangeStatuses = liveExchanges.map((ex) => ({
    exchange: ex.exchange,
    connected: ex.connected,
  }));
  // Signal leaderboard has no real telemetry source yet -> honest empty state.
  const symbolStats: never[] = [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      <div className="container mx-auto p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Trading War Room
            </h1>
            <p className="text-muted-foreground mt-1 flex items-center gap-2">
              Autonomous Trading • Live Quantum State • Temporal Ladder
              {globalState.isRunning && (
                <Badge variant="default" className="bg-success">
                  Systems online
                </Badge>
              )}
              {hncGamma != null && (
                <Badge variant="outline" className="border-primary/40 text-primary"
                       title="Real HNC coherence (gamma) from the operator (/api/pulse)">
                  HNC coherence {(hncGamma * 100).toFixed(1)}%
                </Badge>
              )}
            </p>
          </div>
        </div>

        {/* MAIN LAUNCH BUTTON */}
        <LaunchButton 
          onLaunch={launchAssault}
          onStop={emergencyStop}
          status={state.status}
        />

        {/* Trade Controls Header with Mode Toggle */}
        <TradeControlsHeader
          onLaunchAssault={launchAssault}
          onEmergencyStop={emergencyStop}
          status={state.status}
          tradesExecuted={state.tradesExecuted}
          netPnL={state.netPnL}
          currentBalance={state.currentBalance}
        />

        {/* Trading Status + Readiness */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <TradingStatusPanel />
          <TradingReadinessCheck />
          <CredentialStatusPanel userId={globalState.userId} />
          <GasTankDisplay 
            userId={globalState.userId || 'demo-user'} 
            onEmpty={emergencyStop}
          />
        </div>

        {/* Quantum State */}
        <QuantumStatePanel 
          quantumState={state.quantumState} 
          hiveMindCoherence={state.hiveMindCoherence}
        />

        {/* Prime Seal + Prism + Probability Fusion */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <PrimeSealStatusPanel />
          <PrismFrequencyPanel />
          <ProbabilityFusionPanel />
        </div>

        {/* Active Positions + Live Trade Stream */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ActivePositionsPanel />
          <LiveTradeStream />
        </div>

        {/* Exchange scouts + signal leaderboard */}
        <div className="space-y-4">
          {/* Exchange scout intel + signal leaderboard */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <DuckCommandoIntel exchangeStatuses={exchangeStatuses} showLore={false} />
            <SniperLeaderboard symbolStats={symbolStats} sortBy="kills" maxDisplay={10} />
          </div>
        </div>

        {/* Live Strike Stream */}
        <LiveStrikeStream />

        {/* Historical Timeline */}
        <HistoricalTimeline />

        {/* Unified Bus Status */}
        <UnifiedBusStatus />

        {/* Temporal Ladder + Full Ecosystem */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <TemporalLadderStatus />
          <FullEcosystemStatus />
        </div>

        {/* Multi-Exchange Panel */}
        <MultiExchangePanel />

        {/* System Health Panel */}
        <SystemHealthPanel />

        {/* Auris Nodes Orbit */}
        <AurisNodesOrbit quantumState={state.quantumState} />

        {/* Projection Horizon */}
        <ProjectionHorizon />
      </div>
    </div>
  );
}
