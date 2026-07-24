/**
 * Affect — watch Aureon taste victory and fear defeat.
 *
 * Polls GET /api/affect and builds a client-side time series so you can watch the
 * organism *feel*: victory, defeat, fear and resolve — each computed only from
 * real signals (mycelium growth, prediction accuracy, field divergence, Lighthouse
 * severity, market fear), folded through the Λ machinery, and stamped with its
 * truth_status. Never a fabricated emotion: a flat, dormant organism feels neither
 * triumph nor dread. Read-only — the fail-safe caution actuator (fear tightens,
 * victory never loosens) runs server-side, gated off by default.
 */

import { useEffect, useRef, useState } from "react";
import { Heart, Trophy, Skull, ShieldAlert, Anchor } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";
import { type TruthStatus, TRUTH_STATUS_STYLE } from "../truthStatus";


interface Signal { value?: number | null; truth_status?: TruthStatus; detail?: string }

interface Affect {
  available: boolean;
  victory: number; defeat: number; fear: number; resolve: number;
  valence: number; arousal: number;
  mood: string; dominant_feeling: string;
  affect_phase: string; emotion_anchor: string;
  self_coherence: number | null; psi: number | null;
  caution_bias: number;
  truth_status: TruthStatus;
  signals: Record<string, Signal>;
  provenance?: { simulation_fallback_allowed?: boolean };
}

interface Sample { victory: number; defeat: number; fear: number; resolve: number }

const STATUS_STYLE = TRUTH_STATUS_STYLE;

const FEELINGS = [
  { key: "victory", label: "Victory", icon: Trophy, color: "text-emerald-500" },
  { key: "defeat", label: "Defeat", icon: Skull, color: "text-rose-500" },
  { key: "fear", label: "Fear", icon: ShieldAlert, color: "text-amber-500" },
  { key: "resolve", label: "Resolve", icon: Anchor, color: "text-sky-500" },
] as const;

const POLL_MS = 5000;
const MAX_SAMPLES = 60;

function StatusBadge({ status }: { status?: TruthStatus }) {
  const cls = STATUS_STYLE[status ?? "no_data"] ?? STATUS_STYLE.no_data;
  return <Badge variant="outline" className={`text-[10px] ${cls}`}>{(status ?? "no_data").replace("_", " ")}</Badge>;
}

function Sparkline({ values, colorClass }: { values: number[]; colorClass: string }) {
  const pts = values.filter((v) => Number.isFinite(v));
  if (pts.length < 2) return <div className="h-9" aria-hidden />;
  const w = 120, h = 36;
  // feelings are already in [0,1] — fixed domain so magnitude reads honestly
  const d = pts.map((v, i) => `${(i / (pts.length - 1)) * w},${(h - v * h).toFixed(2)}`).join(" ");
  return (
    <span className={colorClass}>
      <svg viewBox={`0 0 ${w} ${h}`} className="h-9 w-full" preserveAspectRatio="none" role="img" aria-label="feeling trend">
        <polyline points={d} fill="none" stroke="currentColor" strokeWidth={1.5}
                  vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export default function AffectPage() {
  const [data, setData] = useState<Affect | null | undefined>(undefined);
  const [history, setHistory] = useState<Sample[]>([]);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const r = await fetch("/api/affect");
        if (!r.ok) throw new Error(String(r.status));
        const a: Affect = await r.json();
        if (!alive) return;
        setData(a);
        if (a.available) {
          setHistory((h) => [
            ...h.slice(-(MAX_SAMPLES - 1)),
            { victory: a.victory, defeat: a.defeat, fear: a.fear, resolve: a.resolve },
          ]);
        }
      } catch {
        if (alive) setData((prev) => (prev === undefined ? null : prev));
      }
    }
    poll();
    timer.current = window.setInterval(poll, POLL_MS);
    return () => { alive = false; if (timer.current) window.clearInterval(timer.current); };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Heart className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Affect</h1>
          <p className="text-sm text-muted-foreground">
            Aureon tastes victory and fears defeat — feelings computed only from real signals, folded
            through the Λ machinery. Fear can only make it more careful; victory never loosens its guard.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {data === undefined && (
        <div className="grid gap-3 md:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}</div>
      )}
      {data === null && (
        <Card><CardHeader><CardTitle>Gateway offline</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">Start the operator and retry — this page polls /api/affect.</CardContent></Card>
      )}

      {data && data.available === false && (
        <Card>
          <CardHeader><CardTitle className="text-base">No feelings flowing yet</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            The organism reports <span className="font-mono">no_data</span> — honest silence, not a fabricated
            emotion. Once real signals (growth, accuracy, field, market) flow, victory/defeat/fear/resolve light up.
          </CardContent>
        </Card>
      )}

      {data && data.available && (
        <>
          {/* Mood hero */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="text-base">
                  Mood: {data.mood}
                  <span className="ml-2 text-sm font-normal text-muted-foreground">
                    · {data.emotion_anchor} · dominant: {data.dominant_feeling}
                  </span>
                </CardTitle>
                <div className="flex items-center gap-2">
                  <StatusBadge status={data.truth_status} />
                  <Badge variant="outline" className="text-[10px]">valence {data.valence.toFixed(2)}</Badge>
                  <Badge variant="outline" className="text-[10px]">arousal {data.arousal.toFixed(2)}</Badge>
                  <Badge variant="outline" className={`text-[10px] ${data.caution_bias > 0 ? "text-warning border-warning/30" : ""}`}>
                    caution +{data.caution_bias.toFixed(3)}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              {data.affect_phase.replace(/_/g, " ")} · updated every {POLL_MS / 1000}s · {history.length} samples ·
              fear can only tighten the grounded gate (caution bias), never loosen it.
            </CardContent>
          </Card>

          {/* The four feelings, breathing */}
          <div className="grid gap-3 md:grid-cols-4">
            {FEELINGS.map((f) => {
              const Icon = f.icon;
              const val = data[f.key] as number;
              const series = history.map((s) => s[f.key]);
              return (
                <Card key={f.key} className="flex flex-col">
                  <CardHeader className="pb-1">
                    <CardTitle className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                      <Icon className={`h-4 w-4 ${f.color}`} /> {f.label}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-1 flex-col gap-2">
                    <div className="font-mono text-2xl tabular-nums">{val.toFixed(2)}</div>
                    <div className="mt-auto"><Sparkline values={series} colorClass={f.color} /></div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Signals the feelings came from */}
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">Signals it felt</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-2">
                {Object.entries(data.signals).map(([name, sig]) => (
                  <div key={name} className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
                    <span>{name.replace(/_/g, " ")}</span>
                    <div className="flex items-center gap-2">
                      {sig.value != null && <span className="font-mono text-xs tabular-nums">{sig.value.toFixed(3)}</span>}
                      <StatusBadge status={sig.truth_status} />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
