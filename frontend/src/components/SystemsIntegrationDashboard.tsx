/**
 * Systems Integration Dashboard
 * Prime Sentinel: GARY LECKEY 02111991
 *
 * Displays real-time status of all Temporal Ladder systems
 * and their hive mind coherence.
 */

import React, { useEffect, useState } from 'react';
import { useSystemsIntegration, useTemporalLadder, useQueenHiveBrowser } from '../hooks/useSystemsIntegration';
import { SimulatedDataBadge } from '@/components/SimulatedDataBadge';

const SystemStatusCard: React.FC<{
  name: string;
  active: boolean;
  health: number;
  icon: string;
}> = ({ name, active, health, icon }) => {
  const healthColor =
    health > 0.7 ? 'hsl(var(--success))' : health > 0.4 ? 'hsl(var(--warning))' : 'hsl(var(--destructive))';
  const statusText = active ? 'ONLINE' : 'OFFLINE';
  const statusColor = active ? 'hsl(var(--success))' : 'hsl(var(--muted-foreground))';

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
        <span
          className="text-xs font-bold px-2 py-1 rounded text-white"
          style={{ backgroundColor: statusColor }}
        >
          {statusText}
        </span>
      </div>
      <h3 className="text-foreground font-semibold text-sm mb-2">{name}</h3>
      <div className="w-full bg-muted rounded-full h-2">
        <div
          className="h-2 rounded-full transition-all duration-300"
          style={{
            width: `${health * 100}%`,
            backgroundColor: healthColor,
          }}
        />
      </div>
      <span className="text-xs text-muted-foreground mt-1 block">
        Health: {(health * 100).toFixed(0)}%
      </span>
    </div>
  );
};

const SYSTEM_ICONS: Record<string, string> = {
  'harmonic-nexus': '',
  'master-equation': '',
  'earth-integration': '',
  'nexus-feed': '',
  'quantum-quackers': '',
  'akashic-mapper': '',
  'zero-point': '',
  'dimensional-dialler': '',
};

const SYSTEM_DISPLAY_NAMES: Record<string, string> = {
  'harmonic-nexus': 'Harmonic Nexus Core',
  'master-equation': 'Master Equation',
  'earth-integration': 'Earth Integration',
  'nexus-feed': 'Nexus Live Feed',
  'quantum-quackers': 'Quantum Quackers',
  'akashic-mapper': 'Akashic Mapper',
  'zero-point': 'Zero Point Detector',
  'dimensional-dialler': 'Dimensional Dialler',
};

const STAGE_BADGE: Record<string, string> = {
  dominant: 'bg-success text-success-foreground',
  thriving: 'bg-primary text-primary-foreground',
  growing: 'bg-secondary text-secondary-foreground',
  recovering: 'bg-warning text-warning-foreground',
};

export const SystemsIntegrationDashboard: React.FC = () => {
  const { state, isInitialized, refreshAkashic } = useSystemsIntegration();
  const { systemStatuses, hiveMindCoherence } = useTemporalLadder();
  const { state: queenState, step: queenStep, simulate, reset } = useQueenHiveBrowser();

  const [autoSimulate, setAutoSimulate] = useState(false);

  useEffect(() => {
    let interval: number | null = null;
    if (autoSimulate) {
      interval = window.setInterval(() => {
        queenStep();
      }, 500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoSimulate, queenStep]);

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground text-lg">Initializing Hive Mind…</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Temporal Ladder — Hive Mind Integration
          </h1>
          <SimulatedDataBadge />
        </div>
        <p className="text-muted-foreground">
          In-browser systems-integration model
        </p>
      </div>

      {/* Hive Mind Coherence */}
      <div className="mb-8 bg-card rounded-xl p-6 border border-border">
        <h2 className="text-xl font-bold text-foreground mb-4">
          Hive Mind Coherence
        </h2>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="w-full bg-muted rounded-full h-4">
              <div
                className="h-4 rounded-full transition-all duration-500"
                style={{
                  width: `${hiveMindCoherence * 100}%`,
                  background: `linear-gradient(90deg, hsl(var(--primary)), hsl(var(--chart-2)))`,
                }}
              />
            </div>
          </div>
          <span className="text-2xl font-bold text-foreground">
            {(hiveMindCoherence * 100).toFixed(1)}%
          </span>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div className="text-muted-foreground">
            Active Systems: <span className="text-foreground font-bold">{state?.systemsActive || 0}</span>/{state?.systemsTotal || 8}
          </div>
          <div className="text-muted-foreground">
            Integration Health: <span className="text-foreground font-bold">{((state?.integrationHealth || 0) * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* System Grid */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-foreground mb-4">
          System Status
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {systemStatuses.map((system) => (
            <SystemStatusCard
              key={system.name}
              name={SYSTEM_DISPLAY_NAMES[system.name] || system.name}
              active={system.active}
              health={system.health}
              icon={SYSTEM_ICONS[system.name] || ''}
            />
          ))}
        </div>
      </div>

      {/* Akashic Attunement */}
      {state?.akashic && (
        <div className="mb-8 bg-card rounded-xl p-6 border border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-foreground">
              Akashic Attunement
            </h2>
            <button
              onClick={() => refreshAkashic(7)}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-semibold transition"
            >
              Refresh Attunement
            </button>
          </div>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {state.akashic.finalFrequency.toFixed(4)} Hz
              </div>
              <div className="text-muted-foreground text-sm">Final Frequency</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-success">
                {(state.akashic.convergenceRate * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Convergence Rate</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {(state.akashic.stabilityIndex * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Stability Index</div>
            </div>
          </div>
        </div>
      )}

      {/* Zero Point Field */}
      {state?.zeroPoint && (
        <div className="mb-8 bg-card rounded-xl p-6 border border-border">
          <h2 className="text-xl font-bold text-foreground mb-4">
            Zero Point Field
          </h2>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {(state.zeroPoint.zeroPointCoherence * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Coherence</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {(state.zeroPoint.phaseLockStrength * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Phase Lock</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-success">
                {(state.zeroPoint.cavityResonance * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Cavity Resonance</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-primary">
                {state.zeroPoint.activeSeal?.name || 'None'}
              </div>
              <div className="text-muted-foreground text-sm">Active Seal</div>
            </div>
          </div>
        </div>
      )}

      {/* Dimensional Dialler */}
      {state?.dimensional && (
        <div className="mb-8 bg-card rounded-xl p-6 border border-border">
          <h2 className="text-xl font-bold text-foreground mb-4">
            Dimensional Dialler
          </h2>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-success">
                {(state.dimensional.stability.overall * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Overall Stability</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {(state.dimensional.stability.primeAlignment * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Prime Alignment</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {(state.dimensional.stability.schumannHold * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Schumann Hold</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {(state.dimensional.temporalSync * 100).toFixed(1)}%
              </div>
              <div className="text-muted-foreground text-sm">Temporal Sync</div>
            </div>
          </div>
        </div>
      )}

      {/* Queen Hive */}
      {queenState && (
        <div className="mb-8 bg-card rounded-xl p-6 border border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-foreground">
              Queen Hive — 10-9-1 Model
            </h2>
            <div className="flex gap-2">
              <button
                onClick={queenStep}
                className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-semibold transition"
              >
                Step
              </button>
              <button
                onClick={() => simulate(10)}
                className="px-4 py-2 bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded-lg text-sm font-semibold transition"
              >
                +10 Steps
              </button>
              <button
                onClick={() => setAutoSimulate(!autoSimulate)}
                className={`px-4 py-2 ${autoSimulate ? 'bg-destructive hover:bg-destructive/90' : 'bg-success hover:bg-success/90'} text-white rounded-lg text-sm font-semibold transition`}
              >
                {autoSimulate ? 'Stop' : 'Auto'}
              </button>
              <button
                onClick={reset}
                className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-lg text-sm font-semibold transition"
              >
                Reset
              </button>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 text-center mb-4">
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {queenState.totalHives}
              </div>
              <div className="text-muted-foreground text-sm">Total Hives</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-success">
                £{queenState.totalEquity.toFixed(2)}
              </div>
              <div className="text-muted-foreground text-sm">Total Equity</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                {queenState.totalAgents}
              </div>
              <div className="text-muted-foreground text-sm">Total Agents</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-foreground">
                G{queenState.generation}
              </div>
              <div className="text-muted-foreground text-sm">Generation</div>
            </div>
          </div>
          {queenState.hives.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-muted-foreground">
                <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                  <tr>
                    <th className="px-4 py-2">Hive</th>
                    <th className="px-4 py-2">Gen</th>
                    <th className="px-4 py-2">Agents</th>
                    <th className="px-4 py-2">Equity</th>
                    <th className="px-4 py-2">Stage</th>
                    <th className="px-4 py-2">Multiplier</th>
                  </tr>
                </thead>
                <tbody>
                  {queenState.hives.slice(0, 10).map((hive) => (
                    <tr key={hive.id} className="border-b border-border">
                      <td className="px-4 py-2 font-medium text-foreground">{hive.id}</td>
                      <td className="px-4 py-2">{hive.generation}</td>
                      <td className="px-4 py-2">{hive.agents}</td>
                      <td className="px-4 py-2">£{hive.equity.toFixed(2)}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs ${STAGE_BADGE[hive.stage] || 'bg-destructive text-destructive-foreground'}`}>
                          {hive.stage}
                        </span>
                      </td>
                      <td className="px-4 py-2">{hive.profitMultiplier.toFixed(2)}×</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SystemsIntegrationDashboard;
