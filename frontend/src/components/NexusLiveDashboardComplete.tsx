// Nexus Live Dashboard — Complete Harmonic Nexus Charter Console
// Real-time biofield validation instrument with closed feedback loop
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { LiveDataPuller } from "./LiveDataPuller";
import { useHarmonicAuth } from "@/hooks/useHarmonicAuth";
import { fmt } from "@/utils/number";

function clamp01(x: number): number { return Math.max(0, Math.min(1, x)); }
function hsl(h:number, s:number, l:number){ return `hsl(${h} ${s}% ${l}%)`; }

// ---------- types ----------
export type AurisMetrics = {
  ts?: string;
  coherence_score?: number;
  schumann_lock?: number;
  tsv_gain?: number;
  prime_alignment?: number;
  ten_nine_one_concordance?: number;
};

export type AuraMetrics = {
  ts?: string;
  alpha_theta_ratio?: number;
  hrv_norm?: number;
  gsr_norm?: number;
  prime_concordance_10_9_1?: number;
  calm_index?: number;
  aura_hue_deg?: number;
}

// ---------- AuraRing ----------
function AuraRing({m}:{m: AuraMetrics}){
  const hue = Number.isFinite(m?.aura_hue_deg as number) ? (m.aura_hue_deg as number) : 160;
  const glow = 10 + 50*clamp01(m?.calm_index ?? 0);
  const sat  = 40 + 40*clamp01(m?.prime_concordance_10_9_1 ?? 0);
  const light= 45 + 10*clamp01(m?.hrv_norm ?? 0);
  const ring = useMemo(()=>({
    stroke: hsl(hue, sat, light),
    fill:   hsl(hue, Math.min(90, sat+10), Math.min(80, light+10))
  }), [hue, sat, light]);
  return (
    <div className="relative grid place-items-center">
      <svg width="240" height="240" viewBox="0 0 240 240">
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={glow}/>
          </filter>
        </defs>
        <circle cx="120" cy="120" r="86" stroke={ring.stroke} strokeWidth="12" fill="none" filter="url(#glow)"/>
        <circle cx="120" cy="120" r="78" fill={ring.fill} opacity="0.25"/>
      </svg>
      <div className="absolute bottom-3 text-xs text-foreground bg-background/70 px-2 py-1 rounded-xl">
        calm {fmt(m?.calm_index,2)} · 10:9:1 {fmt(m?.prime_concordance_10_9_1,2)}
      </div>
    </div>
  );
}

// ---------- Identity + Role ----------
function deriveT0Hz(dobISO: string){
  if(!dobISO) return 2911.91;
  const d = new Date(dobISO + "T00:00:00Z");
  const jd = Math.floor(d.getTime()/86400000) + 2440588;
  const frac = (jd % 1000) / 1000;
  return +( (2000 + frac*1000).toFixed(2) );
}

function roleFrom(m: AurisMetrics, a: AuraMetrics){
  const C = m?.coherence_score ?? 0;
  const L = m?.schumann_lock ?? 0;
  const X = m?.ten_nine_one_concordance ?? 0;
  const calm = a?.calm_index ?? 0;
  if (C>=0.45 && L>=0.60 && X>=0.65) return {label:"Prime Sentinel (Active)", tone:"emerald"};
  if ((C>=0.25 && L>=0.45) || calm>=0.65) return {label:"Field Harmonizer", tone:"sky"};
  return {label:"Observer / Calibrator", tone:"zinc"};
}

function ToneBadge({tone, children}:{tone:string; children:React.ReactNode}){
  const map: Record<string,string> = {
    emerald: "bg-success/15 text-success ring-success/30",
    sky:     "bg-primary/15 text-primary ring-primary/30",
    zinc:    "bg-muted/40 text-foreground ring-border",
  };
  return <span className={`px-2 py-1 rounded-xl text-xs ring-1 ${map[tone]||map.zinc}`}>{children}</span>
}

// ---------- Main Dashboard ----------
// ---------- Main Dashboard ----------
import { useAurisWS, HarmonicControls } from "./NexusWebSocket";
import { useLatency } from "./LatencyHook";
export default function NexusLiveDashboard(){
  const {connected, auris, aura, wsCtl} = useAurisWS();
  const latency = useLatency("ws://localhost:8787");
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [t0, setT0] = useState<string>("");

  const t0Hz = useMemo(() => t0 ? Number(t0) : deriveT0Hz(dob), [t0, dob]);
  const phiGaia = useMemo(() => +(t0Hz * 1.618).toFixed(2), [t0Hz]);
  const role = roleFrom(auris, aura);

  const handleControlUpdate = (params: any) => {
    // Send control updates to validators via WebSocket
    if (wsCtl.current && wsCtl.current.readyState === 1){
      wsCtl.current.send(JSON.stringify({type: "control", ...params}));
    }
  };

  const handleSnapshot = () => {
    const payload = {
      type: "snapshot",
      at: new Date().toISOString(),
      identity: { name, dob, t0Hz },
      controls: { gain: 0.5, targets_hz: [t0Hz, phiGaia] },
      last_lattice: auris ?? null,
      last_aura: aura ?? null
    };
    if (wsCtl.current && wsCtl.current.readyState === 1){
      wsCtl.current.send(JSON.stringify(payload));
    }
  };

  return (
    <div className="bg-background text-foreground p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="text-center flex-1">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Harmonic Nexus Charter</h1>
            <p className="text-muted-foreground">Real-time biofield validation instrument</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className={`flex items-center gap-2 ${connected?'text-success':'text-muted-foreground'}`}>
              <span className={`w-2 h-2 rounded-full ${connected? 'bg-success':'bg-muted-foreground'}`}></span>
              {connected? 'stream connected':'waiting for stream'}
            </div>
            <div className="px-2 py-1 rounded-lg bg-card text-muted-foreground font-mono">
              {latency !== null ? `${latency} ms` : '— ms'}
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Identity Panel */}
          <div className="bg-card/50 rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold">Identity Binding</h2>
            <div className="space-y-3">
              <input 
                type="text" 
                value={name} 
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-muted text-foreground px-3 py-2 rounded-lg"
                placeholder="Full Name"
              />
              <input 
                type="date" 
                value={dob} 
                onChange={(e) => setDob(e.target.value)}
                className="w-full bg-muted text-foreground px-3 py-2 rounded-lg"
              />
              <input 
                type="number" 
                value={t0} 
                onChange={(e) => setT0(e.target.value)}
                className="w-full bg-muted text-foreground px-3 py-2 rounded-lg"
                placeholder={`t₀ Hz (auto: ${t0Hz})`}
              />
            </div>
            <div className="pt-4 border-t border-border">
              <div className="text-sm text-muted-foreground">φ·Gaia: {phiGaia} Hz</div>
              <div className="mt-2"><ToneBadge tone={role.tone}>{role.label}</ToneBadge></div>
            </div>
          </div>

          {/* Aura Ring */}
          <div className="bg-card/50 rounded-xl p-6">
            <h2 className="text-xl font-semibold mb-4">Aura Field</h2>
            <AuraRing m={aura} />
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <div>HRV: {fmt(aura?.hrv_norm)}</div>
              <div>GSR: {fmt(aura?.gsr_norm)}</div>
              <div>α/θ: {fmt(aura?.alpha_theta_ratio)}</div>
              <div>Hue: {fmt(aura?.aura_hue_deg,0)}°</div>
            </div>
          </div>

          {/* Lattice Metrics */}
          <div className="bg-card/50 rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold">Lattice Metrics</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Coherence:</span>
                <span className="font-mono">{fmt(auris?.coherence_score)}</span>
              </div>
              <div className="flex justify-between">
                <span>Schumann Lock:</span>
                <span className="font-mono">{fmt(auris?.schumann_lock)}</span>
              </div>
              <div className="flex justify-between">
                <span>TSV Gain:</span>
                <span className="font-mono">{fmt(auris?.tsv_gain)}</span>
              </div>
              <div className="flex justify-between">
                <span>Prime Align:</span>
                <span className="font-mono">{fmt(auris?.prime_alignment)}</span>
              </div>
              <div className="flex justify-between">
                <span>10-9-1:</span>
                <span className="font-mono">{fmt(auris?.ten_nine_one_concordance)}</span>
              </div>
            </div>
          </div>

          {/* Controls */}
          <div className="lg:col-span-3">
            <HarmonicControls onUpdate={handleControlUpdate} />
            <div className="mt-4 text-center">
              <button
                onClick={handleSnapshot}
                className="px-6 py-3 rounded-xl bg-success hover:bg-success text-foreground font-medium transition-colors">
                Snapshot Current State ⌘S
              </button>
            </div>
          </div>

          {/* Live Data Streams */}
          <div className="lg:col-span-3">
            <LiveDataPuller />
          </div>

        </div>
      </div>
    </div>
  );
}

export { NexusLiveDashboard as NexusLiveDashboardComplete };
