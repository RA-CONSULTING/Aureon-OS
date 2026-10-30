/**
 * CinematicScene - Three.js Canvas wrapper combining all 3D scene elements
 * The cosmos rendered through @react-three/fiber
 */

import { Suspense, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { CosmicEnvironment } from './CosmicEnvironment';
import { QueenCore } from './QueenCore';
import { HiveConstellation } from './HiveConstellation';
import { TradeBeamSystem } from './TradeBeamSystem';
import { MarketNebula } from './MarketNebula';
import { CoherenceAurora } from './CoherenceAurora';
import { ExchangeGateways } from './ExchangeGateways';
import { MetricRings } from './MetricRings';
import { CinematicCamera } from './CinematicCamera';
import { EventSpotlight } from './EventSpotlight';
import type { GlobalState } from '@/core/globalSystemsManager';
import type { NarratorEventType } from './NarratorEngine';

interface CinematicSceneProps {
  state: GlobalState;
  hiveMood: string;
  activeEvent?: NarratorEventType | null;
}

function SceneContent({ state, hiveMood, activeEvent }: CinematicSceneProps) {
  const latestTradeRef = useRef<{ timestamp: number; side: string; exchange?: string } | null>(null);
  const c = state.consciousness;

  // Track latest trade for camera events
  if (state.recentTrades.length > 0) {
    const latest = state.recentTrades[0];
    const ts = new Date(latest.time).getTime();
    if (!latestTradeRef.current || ts !== latestTradeRef.current.timestamp) {
      latestTradeRef.current = { timestamp: ts, side: latest.side, exchange: latest.exchange };
    }
  }

  const winRate =
    typeof state.totalTrades === 'number' &&
    state.totalTrades > 0 &&
    typeof state.winningTrades === 'number'
      ? (state.winningTrades / state.totalTrades) * 100
      : null;

  // Use consciousness psi for aurora, fall back to coherence (0 only drives 3D visuals)
  const rawCoherence = c.available ? c.psi : state.coherence;
  const effectiveCoherence =
    typeof rawCoherence === 'number' && Number.isFinite(rawCoherence) ? rawCoherence : 0;
  const hasNewThought = c.thoughtStream.length > 0 || !!(state.queenVoice?.text);

  return (
    <>
      {/* Camera director - responds to narrator events */}
      <CinematicCamera
        volatility={Math.max(state.marketData.volatility / 100, c.fearLevel * 0.5)}
        activeEvent={activeEvent}
        tradeExchange={latestTradeRef.current?.exchange}
      />

      {/* Deep space environment */}
      <CosmicEnvironment />

      {/* The Queen - driven by consciousness psi, gamma, reality state */}
      <QueenCore
        coherence={c.available ? c.psi : state.coherence}
        prismState={state.prismState}
        queenState={state.queenState}
        hncMarketState={c.available ? c.realityState : state.hncMarketState}
        lambda={c.available ? c.gamma : state.lambda}
      />

      {/* Hive agents orbiting */}
      <HiveConstellation
        hiveCount={state.myceliumHives}
        agentCount={Math.max(state.myceliumAgents, c.branches * 3)}
        generation={state.myceliumGeneration}
        queenPnl={state.queenPnl}
        coherence={effectiveCoherence}
      />

      {/* Trade execution beams */}
      <TradeBeamSystem recentTrades={state.recentTrades} />

      {/* Market data nebula - consciousness confidence affects color */}
      <MarketNebula
        volatility={state.marketData.volatility}
        momentum={state.marketData.momentum}
        coherence={c.available ? c.selfCoherence : state.coherence}
        hncFrequency={state.hncFrequency}
      />

      {/* Consciousness aurora - driven by thought generation and psi */}
      <CoherenceAurora
        coherence={effectiveCoherence}
        lambda={c.available ? c.lambdaT : state.lambda}
        gaiaFrequency={state.gaiaFrequency}
        hasNewThought={hasNewThought}
      />

      {/* Exchange portals */}
      <ExchangeGateways
        krakenEquity={state.unifiedMarketSummary?.krakenEquity ?? null}
        capitalEquity={state.unifiedMarketSummary?.capitalEquityGbp ?? null}
        krakenConnected={state.ecosystemHealth === 'connected'}
        capitalConnected={state.ecosystemHealth === 'connected'}
        binanceConnected={false}
      />

      {/* Orbital metric rings */}
      <MetricRings
        totalEquity={state.totalEquity ?? 0}
        coherence={effectiveCoherence}
        totalTrades={state.totalTrades ?? 0}
        winRate={winRate ?? 0}
        totalPnl={state.totalPnl ?? 0}
      />

      {/* Dynamic post-processing - responds to events */}
      <EventSpotlight activeEvent={activeEvent || null} />
    </>
  );
}

export function CinematicScene({ state, hiveMood, activeEvent }: CinematicSceneProps) {
  return (
    <div className="absolute inset-0">
      <Canvas
        camera={{ position: [0, 8, 25], fov: 55, near: 0.1, far: 200 }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
          stencil: false,
          depth: true,
        }}
        dpr={[1, 1.5]}
        style={{ background: '#000005' }}
      >
        <Suspense fallback={null}>
          <SceneContent state={state} hiveMood={hiveMood} activeEvent={activeEvent} />
        </Suspense>
      </Canvas>
    </div>
  );
}
