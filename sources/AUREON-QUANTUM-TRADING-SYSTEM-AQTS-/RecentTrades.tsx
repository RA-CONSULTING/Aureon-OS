import React, { useEffect, useMemo, useState } from 'react';

type TradeMap = Record<string, Array<{ id?: number | string; orderId?: number; price: string; qty?: string; qtyInQuote?: string; time: number }>>;

type ApiResp = { trades: TradeMap; mock?: boolean };

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

function fmtTime(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleTimeString();
}

const RecentTrades: React.FC<{ symbols?: string } > = ({ symbols = 'ETHUSDT,BTCUSDT,BNBUSDT,SOLUSDT,ADAUSDT' }) => {
  const [data, setData] = useState<ApiResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const query = useMemo(() => `/api/trades?symbols=${encodeURIComponent(symbols)}`, [symbols]);

  useEffect(() => {
    let mounted = true;
    const tick = async () => {
      try {
        const res = await fetchJson(query);
        if (!mounted) return;
        setData(res);
        setErr(null);
      } catch (e: any) {
        if (!mounted) return;
        setErr(e.message);
      }
    };
    tick();
    const id = setInterval(tick, 7000);
    return () => { mounted = false; clearInterval(id); };
  }, [query]);

  const trades = data?.trades || {};
  const symbolsList = Object.keys(trades);

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-gray-200 font-semibold">Recent Trades</h4>
        {data?.mock && <span className="text-[10px] text-amber-300">MOCK</span>}
      </div>
      {err && <div className="text-xs text-red-400 mb-2">{err}</div>}
      {symbolsList.length === 0 ? (
        <div className="text-xs text-gray-400">No trades available.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
          {symbolsList.map((sym) => (
            <div key={sym} className="bg-gray-900/40 rounded p-2">
              <div className="text-gray-300 font-semibold mb-1">{sym}</div>
              <div className="space-y-1 max-h-48 overflow-auto">
                {(() => {
                  const arr = (trades[sym] || []).slice().reverse();
                  return arr.map((t, idx) => {
                    const prev = idx > 0 ? arr[idx-1] : undefined;
                    const pNow = Number(t.price);
                    const pPrev = prev ? Number(prev.price) : undefined;
                    const ch = pPrev ? (pNow - pPrev) / pPrev : 0;
                    const color = ch > 0 ? 'text-green-400' : ch < 0 ? 'text-red-400' : 'text-gray-400';
                    return (
                      <div key={(t.id ?? t.orderId ?? idx)+''} className="flex items-center justify-between gap-2">
                        <div className="text-gray-400">{fmtTime(t.time)}</div>
                        <div className="text-gray-200 font-mono">{pNow.toFixed(6)}</div>
                        <div className={`font-mono ${color}`}>{pPrev ? `${(ch*100).toFixed(2)}%` : ''}</div>
                        <div className="text-gray-400 font-mono">{t.qty ? Number(t.qty).toFixed(6) : ''}</div>
                      </div>
                    );
                  })
                })()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecentTrades;
