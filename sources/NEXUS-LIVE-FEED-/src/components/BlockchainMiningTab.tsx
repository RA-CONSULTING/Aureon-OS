import { useCallback, useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

type MiningTrend = 'up' | 'down' | 'stable';

export type MiningMetric = {
  id: string;
  label: string;
  value: string;
  delta: string;
  trend: MiningTrend;
  description: string;
};

type MiningNodeStatus = 'Online' | 'Syncing' | 'Maintenance';

export type MiningNode = {
  id: string;
  name: string;
  location: string;
  hashRate: string;
  status: MiningNodeStatus;
  uptime: string;
  energy: string;
  consensusRole: string;
};

export type EnergyChannel = {
  id: string;
  source: string;
  percentage: number;
  status: 'Primary' | 'Supplemental' | 'Reserve';
};

type BlockchainMiningTabProps = {
  metrics: MiningMetric[];
  nodes: MiningNode[];
  ledgerHighlights: string[];
  energyMix: EnergyChannel[];
};

type TransferReceipt = {
  id: string;
  amount: number;
  address: string;
  timestamp: string;
  status: 'processing' | 'completed' | 'error';
};

const trendStyles: Record<MiningTrend, string> = {
  up: 'text-emerald-300',
  down: 'text-rose-300',
  stable: 'text-slate-300',
};

const trendPrefix: Record<MiningTrend, string> = {
  up: '+',
  down: '−',
  stable: '',
};

const nodeStatusVariant: Record<MiningNodeStatus, 'success' | 'info' | 'warning'> = {
  Online: 'success',
  Syncing: 'info',
  Maintenance: 'warning',
};

const nodeAccent: Record<MiningNodeStatus, string> = {
  Online: 'from-emerald-500/40 via-teal-500/25 to-transparent',
  Syncing: 'from-sky-500/45 via-indigo-500/25 to-transparent',
  Maintenance: 'from-amber-500/45 via-rose-500/25 to-transparent',
};

const channelAccent: Record<EnergyChannel['status'], string> = {
  Primary: 'from-emerald-400 via-sky-400 to-cyan-400',
  Supplemental: 'from-amber-400 via-rose-400 to-fuchsia-400',
  Reserve: 'from-slate-400 via-blue-400 to-purple-400',
};

const BLOCKS_PER_SECOND = 0.0325;
const REWARD_PER_BLOCK = 0.125; // Simulated BNB payout per block
const MINIMUM_TRANSFER = 0.05;

const parseNumber = (value: string) => {
  const parsed = Number(value.replace(/[^0-9.]/g, ''));
  return Number.isFinite(parsed) ? parsed : 0;
};

const formatDuration = (seconds: number) => {
  if (seconds <= 0) return '0s';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const parts = [];
  if (h) parts.push(`${h}h`);
  if (m) parts.push(`${m}m`);
  if (s || parts.length === 0) parts.push(`${s}s`);
  return parts.join(' ');
};

const formatReward = (amount: number) => (amount >= 1 ? amount.toFixed(3) : amount.toFixed(5));

const BlockchainMiningTab = ({ metrics, nodes, ledgerHighlights, energyMix }: BlockchainMiningTabProps) => {
  const [isMining, setIsMining] = useState(false);
  const [runtimeSeconds, setRuntimeSeconds] = useState(0);
  const [minedBlocks, setMinedBlocks] = useState(0);
  const [pendingReward, setPendingReward] = useState(0);
  const [walletAddress, setWalletAddress] = useState('');
  const [transferHistory, setTransferHistory] = useState<TransferReceipt[]>([]);
  const [transferStatus, setTransferStatus] = useState<'idle' | 'processing' | 'success' | 'error'>('idle');
  const [transferMessage, setTransferMessage] = useState('');

  const baseHashRate = useMemo(() => parseNumber(metrics.find((metric) => metric.id === 'hashrate')?.value ?? '0'), [
    metrics,
  ]);
  const baseBlockHeight = useMemo(
    () => Math.floor(parseNumber(metrics.find((metric) => metric.id === 'block-height')?.value ?? '0')),
    [metrics],
  );
  const baseLatency = useMemo(() => parseNumber(metrics.find((metric) => metric.id === 'validation-latency')?.value ?? '0'), [
    metrics,
  ]);
  const baseEfficiency = useMemo(
    () => parseNumber(metrics.find((metric) => metric.id === 'pool-efficiency')?.value ?? '0'),
    [metrics],
  );

  useEffect(() => {
    if (!isMining) {
      return;
    }

    const interval = window.setInterval(() => {
      setRuntimeSeconds((prev) => prev + 1);
      setMinedBlocks((prev) => prev + BLOCKS_PER_SECOND);
      setPendingReward((prev) => prev + BLOCKS_PER_SECOND * REWARD_PER_BLOCK);
    }, 1000);

    return () => window.clearInterval(interval);
  }, [isMining]);

  const totalTransferred = useMemo(
    () => transferHistory.reduce((sum, record) => (record.status === 'completed' ? sum + record.amount : sum), 0),
    [transferHistory],
  );

  const dynamicMetrics = useMemo(() => {
    const blockIncrement = Math.floor(minedBlocks);
    return metrics.map((metric) => {
      if (metric.id === 'hashrate') {
        const dynamicHashRate = baseHashRate + (isMining ? Math.log1p(runtimeSeconds) * 0.08 : 0);
        const deltaValue = dynamicHashRate - baseHashRate;
        const deltaPercent = baseHashRate > 0 ? (deltaValue / baseHashRate) * 100 : 0;
        let trend: MiningTrend = 'stable';
        if (deltaPercent > 0.25) trend = 'up';
        if (deltaPercent < -0.25) trend = 'down';
        return {
          ...metric,
          value: `${dynamicHashRate.toFixed(2)} PH/s`,
          delta: `${deltaPercent >= 0 ? '+' : ''}${deltaPercent.toFixed(1)}%`,
          trend,
        };
      }

      if (metric.id === 'block-height') {
        const dynamicHeight = baseBlockHeight + blockIncrement;
        return {
          ...metric,
          value: dynamicHeight.toLocaleString(),
          delta: `${blockIncrement} blocks`,
          trend: blockIncrement > 0 ? 'up' : 'stable',
        };
      }

      if (metric.id === 'validation-latency') {
        const dynamicLatency = Math.max(baseLatency - runtimeSeconds * 0.002, 0.9);
        const deltaValue = baseLatency - dynamicLatency;
        return {
          ...metric,
          value: `${dynamicLatency.toFixed(2)} s`,
          delta: `${deltaValue >= 0 ? '−' : '+'}${Math.abs(deltaValue).toFixed(2)} s`,
          trend: deltaValue > 0.01 ? 'down' : deltaValue < -0.01 ? 'up' : 'stable',
        };
      }

      if (metric.id === 'pool-efficiency') {
        const dynamicEfficiency = Math.min(baseEfficiency + Math.min(runtimeSeconds * 0.0025, 1.2), 99.9);
        const deltaValue = dynamicEfficiency - baseEfficiency;
        return {
          ...metric,
          value: `${dynamicEfficiency.toFixed(1)}%`,
          delta: `${deltaValue >= 0 ? '+' : ''}${deltaValue.toFixed(1)}%`,
          trend: deltaValue > 0.2 ? 'up' : deltaValue < -0.2 ? 'down' : 'stable',
        };
      }

      return metric;
    });
  }, [
    baseBlockHeight,
    baseEfficiency,
    baseHashRate,
    baseLatency,
    isMining,
    metrics,
    minedBlocks,
    runtimeSeconds,
  ]);

  const handleStartMining = useCallback(() => {
    setTransferStatus('idle');
    setTransferMessage('');
    setIsMining(true);
  }, []);

  const handleStopMining = useCallback(() => {
    setIsMining(false);
  }, []);

  const handleTransfer = useCallback(() => {
    const normalizedAddress = walletAddress.trim();

    if (!normalizedAddress) {
      setTransferStatus('error');
      setTransferMessage('Enter a Binance Smart Chain wallet address before attempting a transfer.');
      return;
    }

    if (pendingReward < MINIMUM_TRANSFER) {
      setTransferStatus('error');
      setTransferMessage(`Accumulate at least ${MINIMUM_TRANSFER} BNB before requesting a payout.`);
      return;
    }

    const transferAmount = Number(pendingReward.toFixed(6));
    const timestamp = new Date().toISOString();
    const transferId = `${timestamp}-${Math.random().toString(36).slice(2, 8)}`;

    const queuedReceipt: TransferReceipt = {
      id: transferId,
      amount: transferAmount,
      address: normalizedAddress,
      timestamp,
      status: 'processing',
    };

    setTransferStatus('processing');
    setTransferMessage('Authorizing simulated payout with Binance Smart Chain validators...');
    setTransferHistory((prev) => [queuedReceipt, ...prev].slice(0, 12));

    window.setTimeout(() => {
      setTransferHistory((prev) =>
        prev.map((entry) => (entry.id === transferId ? { ...entry, status: 'completed' } : entry)),
      );
      setPendingReward((prev) => Math.max(0, prev - transferAmount));
      setTransferStatus('success');
      setTransferMessage(`Simulated transfer of ${formatReward(transferAmount)} BNB to ${normalizedAddress}.`);
    }, 1400);
  }, [pendingReward, walletAddress]);

  return (
    <Card className="group relative overflow-hidden border-white/10 bg-slate-950/80 text-slate-100 shadow-[0_0_45px_rgba(14,165,233,0.25)]">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-500/20 via-transparent to-emerald-400/20 opacity-80" />
      <div className="pointer-events-none absolute -inset-24 animate-stellar-pulse bg-[radial-gradient(circle,_rgba(34,197,247,0.35),_transparent_60%)] opacity-0 transition duration-700 group-hover:opacity-80" />
      <CardHeader className="relative z-10 pb-6">
        <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Blockchain Mining Lattice</CardTitle>
        <p className="mt-2 max-w-2xl text-sm text-slate-300/85">
          Initiate Nexus mining routines, observe live validator telemetry, and queue simulated BNB payouts to a Binance wallet.
        </p>
      </CardHeader>
      <CardContent className="relative z-10 space-y-8">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {dynamicMetrics.map((metric) => (
            <div
              key={metric.id}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px] shadow-[0_0_35px_rgba(34,197,247,0.28)]"
            >
              <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(circle_at_top,_rgba(34,197,247,0.3),_transparent_65%)] opacity-0 transition duration-500 group-hover:opacity-80" />
              <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-4">
                <div className="relative z-10 flex flex-col gap-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-300/80">{metric.label}</div>
                  <div className="text-3xl font-semibold text-white drop-shadow-[0_0_30px_rgba(255,255,255,0.35)]">{metric.value}</div>
                  <div className={cn('text-xs uppercase tracking-[0.28em]', trendStyles[metric.trend])}>
                    {trendPrefix[metric.trend]}
                    {metric.delta}
                  </div>
                  <p className="text-xs leading-relaxed text-slate-300/75">{metric.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-[2fr_1.2fr]">
          <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px] shadow-[0_0_30px_rgba(56,189,248,0.25)]">
            <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(circle_at_center,_rgba(56,189,248,0.25),_transparent_65%)] opacity-0 transition duration-500 hover:opacity-80" />
            <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
              <div className="flex flex-col gap-4">
                <div className="text-sm font-semibold uppercase tracking-[0.28em] text-white">Node Cohort</div>
                <div className="space-y-4">
                  {nodes.map((node) => (
                    <div key={node.id} className="group relative overflow-hidden rounded-2xl border border-white/5 bg-slate-950/70 p-4">
                      <div className={cn('pointer-events-none absolute inset-0 rounded-2xl opacity-70 blur-xl transition duration-500 group-hover:opacity-100', `bg-gradient-to-br ${nodeAccent[node.status]}`)} />
                      <div className="relative z-10 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                        <div>
                          <div className="text-sm font-semibold uppercase tracking-[0.24em] text-white">{node.name}</div>
                          <div className="text-[11px] uppercase tracking-[0.3em] text-slate-300/70">{node.location}</div>
                        </div>
                        <Badge variant={nodeStatusVariant[node.status]} className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]">
                          {node.status}
                        </Badge>
                      </div>
                      <div className="relative z-10 mt-3 grid gap-2 text-xs uppercase tracking-[0.28em] text-slate-200/80 md:grid-cols-3">
                        <div>
                          <span className="block text-[10px] text-slate-400/80">Hash Rate</span>
                          <span className="text-sm font-semibold text-white">{node.hashRate}</span>
                        </div>
                        <div>
                          <span className="block text-[10px] text-slate-400/80">Uptime</span>
                          <span className="text-sm font-semibold text-white">{node.uptime}</span>
                        </div>
                        <div>
                          <span className="block text-[10px] text-slate-400/80">Consensus Role</span>
                          <span className="text-sm font-semibold text-white">{node.consensusRole}</span>
                        </div>
                      </div>
                      <div className="relative z-10 mt-3 text-[10px] uppercase tracking-[0.32em] text-slate-300/70">Energy · {node.energy}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px] shadow-[0_0_25px_rgba(45,212,191,0.25)]">
              <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(circle_at_center,_rgba(45,212,191,0.25),_transparent_65%)] opacity-0 transition duration-500 hover:opacity-80" />
              <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
                <div className="flex flex-col gap-4">
                  <div className="text-sm font-semibold uppercase tracking-[0.28em] text-white">Mining Control</div>
                  <div className="grid gap-4 text-xs uppercase tracking-[0.24em] text-slate-300/70 sm:grid-cols-2">
                    <div>
                      <span className="block text-[10px] text-slate-400/80">Runtime</span>
                      <span className="text-lg font-semibold text-white">{formatDuration(runtimeSeconds)}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-400/80">Blocks Simulated</span>
                      <span className="text-lg font-semibold text-white">{minedBlocks.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-400/80">Pending Reward</span>
                      <span className="text-lg font-semibold text-white">{formatReward(pendingReward)} BNB</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-400/80">Total Settled</span>
                      <span className="text-lg font-semibold text-white">{formatReward(totalTransferred)} BNB</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <Button
                      onClick={isMining ? handleStopMining : handleStartMining}
                      variant={isMining ? 'secondary' : 'default'}
                      className="rounded-full px-6 text-[11px] uppercase tracking-[0.3em]"
                    >
                      {isMining ? 'Pause Mining' : 'Start Mining'}
                    </Button>
                    <div className="text-[11px] uppercase tracking-[0.26em] text-emerald-300/80">
                      {isMining ? 'Simulating validator rounds…' : 'Mining paused'}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-semibold uppercase tracking-[0.32em] text-slate-300/70">
                      Binance Wallet (BEP-20)
                    </label>
                    <input
                      value={walletAddress}
                      onChange={(event) => setWalletAddress(event.target.value)}
                      placeholder="0x..."
                      className="w-full rounded-full border border-white/10 bg-slate-950/80 px-4 py-2 text-[12px] tracking-[0.18em] text-slate-100 placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
                    />
                    <Button
                      onClick={handleTransfer}
                      disabled={transferStatus === 'processing' || pendingReward < MINIMUM_TRANSFER}
                      className="w-full rounded-full bg-emerald-500/80 px-6 py-2 text-[11px] font-semibold uppercase tracking-[0.3em] text-white hover:bg-emerald-400/90"
                    >
                      Queue Binance Transfer
                    </Button>
                    <p className="text-[10px] leading-relaxed tracking-[0.26em] text-slate-400/80">
                      Transfers are simulated for UI validation only. Provide a Binance Smart Chain address to test the payout flow.
                    </p>
                    {transferStatus !== 'idle' && (
                      <div
                        className={cn(
                          'rounded-xl border px-4 py-3 text-[11px] uppercase tracking-[0.26em]',
                          transferStatus === 'success'
                            ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
                            : transferStatus === 'error'
                              ? 'border-rose-400/30 bg-rose-500/10 text-rose-200'
                              : 'border-sky-400/30 bg-sky-500/10 text-sky-200',
                        )}
                      >
                        {transferMessage}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px] shadow-[0_0_25px_rgba(45,212,191,0.25)]">
              <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(circle_at_center,_rgba(45,212,191,0.25),_transparent_65%)] opacity-0 transition duration-500 hover:opacity-80" />
              <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
                <div className="text-sm font-semibold uppercase tracking-[0.28em] text-white">Ledger Highlights</div>
                <ul className="mt-4 space-y-3 text-sm leading-relaxed text-slate-300/80">
                  {ledgerHighlights.map((highlight, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <span className="mt-1 h-2.5 w-2.5 rounded-full bg-gradient-to-r from-cyan-300 via-emerald-300 to-amber-300 shadow-[0_0_12px_rgba(110,231,183,0.65)]" />
                      <span>{highlight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px] shadow-[0_0_25px_rgba(14,165,233,0.25)]">
              <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(circle_at_center,_rgba(14,165,233,0.3),_transparent_65%)] opacity-0 transition duration-500 hover:opacity-80" />
              <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
                <div className="text-sm font-semibold uppercase tracking-[0.28em] text-white">Energy Mix Channels</div>
                <div className="mt-4 space-y-4">
                  {energyMix.map((channel) => (
                    <div key={channel.id} className="relative overflow-hidden rounded-2xl border border-white/5 bg-slate-950/70 p-4">
                      <div
                        className={cn(
                          'pointer-events-none absolute inset-0 rounded-2xl opacity-70 blur-xl transition duration-500',
                          `bg-gradient-to-r ${channelAccent[channel.status]}`,
                        )}
                      />
                      <div className="relative z-10 flex flex-col gap-2">
                        <div className="flex flex-col gap-1">
                          <div className="text-sm font-semibold uppercase tracking-[0.24em] text-white">{channel.source}</div>
                          <div className="text-[11px] uppercase tracking-[0.3em] text-slate-300/70">{channel.status}</div>
                        </div>
                        <div className="text-2xl font-semibold text-white">{channel.percentage}%</div>
                        <div className="h-2 overflow-hidden rounded-full border border-white/10 bg-white/5">
                          <div
                            className={cn('h-full rounded-full bg-gradient-to-r', `from-white/80 via-white/70 to-white/50`)}
                            style={{ width: `${channel.percentage}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {transferHistory.length > 0 && (
              <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px] shadow-[0_0_25px_rgba(129,140,248,0.25)]">
                <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(circle_at_center,_rgba(129,140,248,0.3),_transparent_65%)] opacity-0 transition duration-500 hover:opacity-80" />
                <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
                  <div className="text-sm font-semibold uppercase tracking-[0.28em] text-white">Transfer Ledger</div>
                  <ul className="mt-4 space-y-3 text-xs leading-relaxed tracking-[0.22em] text-slate-300/80">
                    {transferHistory.slice(0, 6).map((transfer) => (
                      <li
                        key={transfer.id}
                        className="flex flex-col gap-1 rounded-xl border border-white/10 bg-white/5 p-3 text-[11px] uppercase tracking-[0.26em]"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 text-white">
                          <span>{transfer.status === 'completed' ? 'Completed' : 'Processing'}</span>
                          <span>{new Date(transfer.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <div className="text-slate-200">{formatReward(transfer.amount)} BNB → {transfer.address}</div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default BlockchainMiningTab;
