// src/components/VoiceOfReasonPanel.tsx
import React, { useEffect, useMemo, useState } from "react";
import { retrospective, nowcast, forecast, whatIf, type Series, type Sensitivity } from "@/lib/aureon/voice-of-reason";
import { SeroConfig } from "@/lib/sero/sero-core"; // for dual-consent + sim guard
import PrimeSentinelProclamation from "@/components/PrimeSentinelProclamation";
import NorthStarCard from "@/components/NorthStarCard";
import TrueVoiceOfReason from "@/components/TrueVoiceOfReason"; // Import the new component

// Minimal UI primitives you already have: Card, Button, Badge (or replace with divs)
import { Card, CardContent, CardHeader, CardTitle, Badge } from "@/components/ui";

// ---- Replace these adapters with your real data fetchers ----
async function fetchSeries(metricId: string, lookback_ms: number): Promise<Series> {
  const r = await fetch(`/api/chronicle/${encodeURIComponent(metricId)}?lookback_ms=${lookback_ms}`);
  if (!r.ok) return [];
  const rows = await r.json();
  return rows.map((row: any) => ({ t: +new Date(row.ts), v: Number(row.value) || 0 }));
}
async function fetchLatest(metricId: string): Promise<number|null> {
  const r = await fetch(`/api/metric/${encodeURIComponent(metricId)}/latest`);
  if (!r.ok) return null;
  const { value } = await r.json();
  return (value===undefined || value===null) ? null : Number(value);
}

export default function VoiceOfReasonPanel(){
  const [metric, setMetric] = useState("qssr.coherence");
  const [lookback, setLookback] = useState(6*60*60*1000); // 6h
  const [series, setSeries] = useState<Series>([]);
  const [baseline, setBaseline] = useState<number|null>(null);
  const [deltaX, setDeltaX] = useState(0.05); // user “what-if” tweak
  const [loading, setLoading] = useState(false);

  useEffect(()=>{
    let live=true;
    (async()=>{
      setLoading(true);
      const [s, b] = await Promise.all([
        fetchSeries(metric, lookback),
        fetchLatest(metric)
      ]);
      if (!live) return;
      setSeries(s);
      setBaseline(b);
      setLoading(false);
    })();
    return ()=>{ live=false; };
  },[metric, lookback]);

  const retro = useMemo(()=> retrospective(series, lookback), [series, lookback]);
  const now   = useMemo(()=> nowcast(series), [series]);
  const fcast = useMemo(()=> forecast(series, 30*60*1000, 30), [series]); // 30 min horizon

  const sens: Sensitivity = useMemo(()=>({
    metric: metric,
    dY_dX: 1.0,
    clamp_lo: 0,
    clamp_hi: 1
  }),[metric]);
  const scenario = useMemo(()=> whatIf(baseline, deltaX, sens), [baseline, deltaX, sens]);

  return (
    <div className="grid gap-4">
      <PrimeSentinelProclamation />
      <NorthStarCard />
      <div className="flex items-center gap-8">
        <h2 className="text-xl font-semibold">Voice of Reason</h2>
        <div className="text-sm opacity-80">
          Coherence: {now.integrityScore !== null ? `${(now.integrityScore * 100).toFixed(2)}%` : "N/A"}
        </div>
        <div className="ml-auto text-sm opacity-70">
          Mode: {SeroConfig.allowSimulationOnly ? "SIMULATION" : "LIVE"}
        </div>
      </div>

      {/* Controls */}
      <Card>
        <CardHeader><CardTitle>Metric</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-3 items-center">
          <select value={metric} onChange={e=>setMetric(e.target.value)} className="px-3 py-2 rounded bg-transparent border">
            <option value="qssr.coherence">QSSR — Solar Coherence</option>
            <option value="terrestrial.schumann.f1">Schumann f1</option>
            <option value="terrestrial.geomag.kp">Kp Index</option>
            <option value="heliospheric.solarWind.bz">IMF Bz</option>
          </select>
          <select value={lookback} onChange={e=>setLookback(Number(e.target.value))} className="px-3 py-2 rounded bg-transparent border">
            <option value={1*60*60*1000}>Lookback: 1h</option>
            <option value={6*60*60*1000}>Lookback: 6h</option>
            <option value={24*60*60*1000}>Lookback: 24h</option>
          </select>
          <div className="text-sm opacity-70">{loading ? "loading…" : `${retro.n} points`}</div>
        </CardContent>
      </Card>

      {/* What Was */}
      <Card>
        <CardHeader><CardTitle>What was (Retrospective)</CardTitle></CardHeader>
        <CardContent className="text-sm grid gap-2">
          <div>Window: {(retro.window_ms/3600000).toFixed(2)} h</div>
          <div>Mean: {retro.mean.toFixed(4)} | Min: {retro.min.toFixed(4)} | Max: {retro.max.toFixed(4)}</div>
          <div>Trend: {retro.slope_per_hr.toFixed(6)} per hour | Δ%: {retro.change_pct.toFixed(2)}%</div>
          <div>Anomalies: {retro.anomalies.length ? retro.anomalies.length : 0}</div>
        </CardContent>
      </Card>

      {/* What Is */}
      <Card>
        <CardHeader><CardTitle>What is (Nowcast)</CardTitle></CardHeader>
        <CardContent className="text-sm grid gap-2">
          <div>Latest: {baseline==null ? "—" : baseline.toFixed(4)}</div>
          <div>Freshness: {now.freshness_ms==null ? "—" : `${now.freshness_ms} ms`}</div>
          {now.notes.length>0 && <div className="opacity-70">Notes: {now.notes.join("; ")}</div>}
        </CardContent>
      </Card>

      {/* What Shall Be */}
      <Card>
        <CardHeader><CardTitle>What shall be (Forecast)</CardTitle></CardHeader>
        <CardContent className="text-sm grid gap-2">
          <div>Model: {fcast.model} | Horizon: {(fcast.horizon_ms/60000).toFixed(0)} min | RMSE: {isFinite(fcast.rmse)?fcast.rmse.toFixed(4):"—"}</div>
          <div>Next (≈5 min): {
            fcast.yhat[4] ? `${fcast.yhat[4].v.toFixed(4)} [${fcast.yhat[4].lo.toFixed(4)}, ${fcast.yhat[4].hi.toFixed(4)}]` : "—"
          }</div>
        </CardContent>
      </Card>

      {/* What If is now replaced by the True Voice of Reason */}
      <TrueVoiceOfReason />
    </div>
  );
}
