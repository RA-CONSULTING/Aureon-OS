/**
 * CinematicHUD - HTML overlay combining all HUD panels
 * Glassmorphic sci-fi cockpit interface with full consciousness data,
 * documentary narrator, and ambient audio controls
 */

import { HUDTopBar } from './HUDTopBar';
import { HUDQueenVoice } from './HUDQueenVoice';
import { HUDTradeStream } from './HUDTradeStream';
import { HUDMetricsPanel } from './HUDMetricsPanel';
import { HUDConsciousnessPanel } from './HUDConsciousnessPanel';
import { HUDNarrator } from './HUDNarrator';
import { AmbientSoundscape } from './AmbientSoundscape';
import type { GlobalState } from '@/core/globalSystemsManager';
import type { NarratorEventType } from './NarratorEngine';

interface CinematicHUDProps {
  state: GlobalState;
  hiveMood: string;
  activeScanner: string;
  onNarratorEvent?: (event: NarratorEventType) => void;
}

export function CinematicHUD({ state, hiveMood, activeScanner, onNarratorEvent }: CinematicHUDProps) {
  const winRate =
    typeof state.totalTrades === 'number' &&
    state.totalTrades > 0 &&
    typeof state.winningTrades === 'number'
      ? (state.winningTrades / state.totalTrades) * 100
      : null;

  const c = state.consciousness;
  const hudCoherence = c.available ? c.psi : state.coherence;
  const hudLambda = c.available ? c.lambdaT : state.lambda;
  const coherenceForDisplay =
    typeof hudCoherence === 'number' && Number.isFinite(hudCoherence) ? hudCoherence : null;
  const lambdaForDisplay =
    typeof hudLambda === 'number' && Number.isFinite(hudLambda) ? hudLambda : null;

  return (
    <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden">
      {/* Top bar */}
      <HUDTopBar
        totalEquity={state.totalEquity}
        totalPnl={state.totalPnl}
        totalPnlNote={state.totalPnlNote}
        cyclePnlPercent={state.cyclePnlPercent}
        winRate={winRate}
        coherence={coherenceForDisplay}
        totalTrades={state.totalTrades}
        isActive={state.isActive}
        krakenConnected={state.ecosystemHealth === 'connected'}
        capitalConnected={state.ecosystemHealth === 'connected'}
        binanceConnected={false}
      />

      {/* Queen consciousness stream */}
      <HUDQueenVoice
        queenVoice={state.queenVoice}
        mood={c.available ? c.mood : hiveMood}
        queenState={state.queenState}
        activeScanner={activeScanner}
        consciousness={c}
      />

      {/* Trade stream */}
      <HUDTradeStream recentTrades={state.recentTrades} />

      {/* Metrics panel */}
      <HUDMetricsPanel
        coherence={coherenceForDisplay}
        lambda={lambdaForDisplay}
        lighthouseSignal={state.lighthouseSignal}
        prismState={state.prismState}
        hncFrequency={state.hncFrequency}
        hncMarketState={state.hncMarketState}
        gaiaLatticeState={state.gaiaLatticeState}
        gaiaFrequency={state.gaiaFrequency}
        dominantNode={state.dominantNode}
      />

      {/* Consciousness deep metrics panel */}
      {c.available && (
        <HUDConsciousnessPanel consciousness={c} />
      )}

      {/* Documentary narrator - observational captions */}
      <HUDNarrator state={state} onEvent={onNarratorEvent} />

      {/* Ambient soundscape controls */}
      <AmbientSoundscape
        coherence={coherenceForDisplay}
        psi={c.psi}
        fearLevel={c.fearLevel}
        gaiaFrequency={state.gaiaFrequency}
        activeEvent={null}
      />

      {/* Bottom center - title card with dream progress */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
        <div className="text-center">
          {c.available && c.dreamProgress > 0 && (
            <div className="text-[9px] text-white/20 mb-0.5">
              Dream: {(c.dreamProgress * 100).toFixed(4)}% toward ${(c.dreamTarget / 1e9).toFixed(0)}B
            </div>
          )}
          <div className="text-[10px] text-white/15 uppercase tracking-[0.3em] font-light">
            A Song of Space and Time
          </div>
        </div>
      </div>
    </div>
  );
}
