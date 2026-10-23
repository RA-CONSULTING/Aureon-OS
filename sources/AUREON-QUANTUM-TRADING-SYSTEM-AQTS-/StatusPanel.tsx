import React, { useEffect, useState } from 'react';

type BotTail = { name: string; tail: string[] };

const API_BASES = [
  '',
  typeof window !== 'undefined' ? `${window.location.origin}` : '',
  'http://localhost:8787',
];

async function fetchJson(path: string) {
  for (const base of API_BASES) {
    const url = base ? `${base.replace(/\/$/, '')}${path}` : path;
    try {
      const r = await fetch(url);
      if (r.ok) return r.json();
    } catch {}
  }
  throw new Error('All endpoints failed');
}

const StatusPanel: React.FC = () => {
  const [balance, setBalance] = useState<{ eth: number; usdt: number; ethUsdt: number; totalUsd: number; canTrade: boolean } | null>(null);
  const [bots, setBots] = useState<BotTail[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showThresholdAlert, setShowThresholdAlert] = useState<boolean>(false);
  const [eligiblePrev, setEligiblePrev] = useState<boolean | null>(null);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => {
    try {
      return (localStorage.getItem('statusPanel:sound') ?? 'on') !== 'off';
    } catch { return true; }
  });

  useEffect(() => {
    try { localStorage.setItem('statusPanel:sound', soundEnabled ? 'on' : 'off'); } catch {}
  }, [soundEnabled]);

  const playBeep = async () => {
    try {
      const Ctx = (window as any).AudioContext || (window as any).webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      if (ctx.state === 'suspended') {
        try { await ctx.resume(); } catch {}
      }
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine';
      o.frequency.value = 880;
      o.connect(g);
      g.connect(ctx.destination);
      g.gain.setValueAtTime(0.0001, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.06, ctx.currentTime + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.25);
      o.start();
      o.stop(ctx.currentTime + 0.26);
    } catch {}
  };

  const inferBotStatus = (tail: string[]): { label: string; color: string } => {
    const text = tail.join('\n').toLowerCase();
    if (!text) return { label: 'idle', color: 'text-gray-400' };
    if (
      text.includes('waiting for funds') ||
      text.includes('waiting for eth') ||
      text.includes('awaiting funding') ||
      text.includes('insufficient funds') ||
      text.includes('min notional') ||
      text.includes('min_notional') ||
      text.includes('minnotional') ||
      text.includes('balance too low') ||
      text.includes('waiting for')
    ) {
      return { label: 'waiting', color: 'text-amber-300' };
    }
    if (
      text.includes('simulate buy') ||
      text.includes('simulate sell') ||
      text.includes('dry_run') ||
      text.includes('dry-run') ||
      text.includes('dry run') ||
      text.includes('paper') ||
      text.includes('would place') ||
      text.includes('simulat')
    ) {
      return { label: 'simulating', color: 'text-sky-300' };
    }
    if (
      text.includes('✅') ||
      text.includes('bought') ||
      text.includes('sold') ||
      text.includes('real trade') ||
      text.includes('placed order') ||
      text.includes('placing order') ||
      text.includes('orderid') ||
      text.includes('executed') ||
      text.includes('filled') ||
      text.includes('market buy') ||
      text.includes('market sell')
    ) {
      return { label: 'active', color: 'text-green-400' };
    }
    return { label: 'running', color: 'text-gray-300' };
  };

  useEffect(() => {
    let mounted = true;
    const tick = async () => {
      try {
        const [b, bs] = await Promise.all([
          fetchJson('/api/status'),
          fetchJson('/api/bots'),
        ]);
        if (!mounted) return;
        setBalance(b);
        setBots(bs.bots || []);
        setError(null);
        // Threshold crossing alert logic
        const eligible = (b.usdt >= 10) || (b.eth * b.ethUsdt >= 10);
        if (eligiblePrev === null) {
          setEligiblePrev(eligible);
        } else if (eligible && eligiblePrev === false) {
          setShowThresholdAlert(true);
          setEligiblePrev(true);
          setTimeout(() => setShowThresholdAlert(false), 10000);
          if (soundEnabled) playBeep();
        } else if (!eligible && eligiblePrev === true) {
          setEligiblePrev(false);
        }
      } catch (e: any) {
        if (!mounted) return;
        setError(e.message);
      }
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 mb-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-gray-200 font-semibold">Live Status</h4>
        <div className="flex items-center gap-3">
          {balance && (
            <span className="text-xs text-gray-400">ETHUSDT ${balance.ethUsdt.toFixed(2)}</span>
          )}
          <div className="flex items-center gap-2">
            <button
              className={`text-xs px-2 py-1 rounded border ${soundEnabled ? 'border-green-500 text-green-300' : 'border-gray-600 text-gray-300'}`}
              onClick={() => setSoundEnabled((v) => !v)}
              title="Toggle threshold alert sound"
            >
              Sound: {soundEnabled ? 'ON' : 'OFF'}
            </button>
            <button
              className="text-xs px-2 py-1 rounded border border-gray-600 text-gray-300"
              onClick={() => { if (soundEnabled) playBeep(); }}
              title="Play test tone"
            >
              Test
            </button>
          </div>
        </div>
      </div>
      {error && <div className="text-red-400 text-xs mb-2">{error}</div>}
      {showThresholdAlert && (
        <div className="mb-2 rounded bg-green-600/20 border border-green-500/40 text-green-200 text-xs px-3 py-2">
          Trading unlocked: balance &ge; $10 notional. Bots will start.
        </div>
      )}
      {balance ? (
        <div className="grid grid-cols-4 gap-3 text-sm">
          <div className="bg-gray-900/40 rounded p-2">
            <div className="text-gray-400 text-xs">ETH</div>
            <div className="text-gray-100 font-mono">{balance.eth.toFixed(8)}</div>
          </div>
          <div className="bg-gray-900/40 rounded p-2">
            <div className="text-gray-400 text-xs">USDT</div>
            <div className="text-gray-100 font-mono">${balance.usdt.toFixed(2)}</div>
          </div>
          <div className="bg-gray-900/40 rounded p-2">
            <div className="text-gray-400 text-xs">Total (USDT)</div>
            <div className="text-gray-100 font-mono">${balance.totalUsd.toFixed(2)}</div>
          </div>
          <div className="bg-gray-900/40 rounded p-2">
            <div className="text-gray-400 text-xs">Trading</div>
            <div className={`text-gray-100 font-mono ${balance.canTrade ? 'text-green-400' : 'text-red-400'}`}>{balance.canTrade ? 'ENABLED' : 'DISABLED'}</div>
          </div>
        </div>
      ) : (
        <div className="text-xs text-gray-400">Loading status…</div>
      )}

      <div className="bg-gray-900/60 p-4 rounded-lg border border-gray-700 mt-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-white">Bots</h3>
          <span className="text-xs text-gray-400">log tails</span>
        </div>
        {bots.length === 0 ? (
          <div className="text-gray-400 text-xs">No bots reporting yet.</div>
        ) : (
          <div className="space-y-3 max-h-80 overflow-auto">
            {bots.map((b) => {
              const status = inferBotStatus(b.tail || []);
              return (
                <div key={b.name} className="bg-black/30 rounded border border-gray-800">
                  <div className="px-3 py-2 border-b border-gray-800 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs ${status.color}`}>●</span>
                      <div className="text-white font-medium">{b.name}</div>
                      <div className="text-xs text-gray-400">{status.label}</div>
                    </div>
                    <div className="text-xs text-gray-500">latest 20 lines</div>
                  </div>
                  <pre className="text-xs text-gray-300 p-3 whitespace-pre-wrap leading-relaxed">{(b.tail || []).join('\n')}</pre>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatusPanel;
