/**
 * Soul — how Aureon reacts.
 *
 * Polls GET /api/soul: the organism perceives a stimulus, feels it, thinks,
 * takes the counsel of its lineage (conscience/"what would Gary do?", elders,
 * values, goals), and makes a determination of its own mind — or, when its
 * voices genuinely disagree, honestly WAITS ("of two minds — wait for one")
 * rather than fabricate a consensus. Read-only; the live loop and any guarded
 * action run server-side, doubly-gated and off by default.
 */

import { useEffect, useState } from "react";
import { Feather, Check, PauseCircle, Ban } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";
import { type TruthStatus, TRUTH_STATUS_STYLE } from "../truthStatus";


interface Voice { stance?: string; verdict?: string; truth_status?: TruthStatus; [k: string]: unknown }

interface WorkOrder {
  seq: number; role: string; department: string; description: string;
  action: string; risk?: string; requires_human?: boolean;
  outcome?: { dry_run?: boolean; blocked?: boolean; executed?: boolean } | null;
}

interface DirectedPlan {
  intent: string;
  work_orders: WorkOrder[];
  workforce?: { role: string }[];
  risk?: string;
  directed?: boolean;
  truth_status?: TruthStatus;
}

interface Soul {
  available: boolean;
  stance: "act" | "wait" | "refuse";
  resolved: boolean;
  agreement: number;
  determination: string;
  what_gary_would_say: string | null;
  proposed_action: { action: string; params?: Record<string, unknown> } | null;
  plan: DirectedPlan | null;
  mood: string | null;
  voices: Record<string, Voice>;
  dissent: string[];
  truth_status: TruthStatus;
}

const STATUS_STYLE = TRUTH_STATUS_STYLE;

const STANCE = {
  act: { icon: Check, cls: "text-emerald-600", label: "resolved — will act" },
  wait: { icon: PauseCircle, cls: "text-amber-600", label: "of two minds — waiting" },
  refuse: { icon: Ban, cls: "text-rose-600", label: "conscience refused" },
} as const;

function Stance({ stance }: { stance?: string }) {
  return <Badge variant="outline" className="text-[10px]">{stance ?? "—"}</Badge>;
}

export default function SoulPage() {
  const [data, setData] = useState<Soul | null | undefined>(undefined);

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const r = await fetch("/api/soul");
        if (!r.ok) throw new Error(String(r.status));
        const d: Soul = await r.json();
        if (alive) setData(d);
      } catch {
        if (alive) setData((p) => (p === undefined ? null : p));
      }
    }
    poll();
    const t = window.setInterval(poll, 5000);
    return () => { alive = false; window.clearInterval(t); };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Feather className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Soul</h1>
          <p className="text-sm text-muted-foreground">
            Thought, feeling, and the counsel of its lineage — unified into a determination of its own
            mind. When its voices disagree, it waits for one rather than invent a consensus.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {data === undefined && (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}</div>
      )}
      {data === null && (
        <Card><CardHeader><CardTitle>Gateway offline</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">Start the operator and retry — this page polls /api/soul.</CardContent></Card>
      )}

      {data && data.available === false && (
        <Card>
          <CardHeader><CardTitle className="text-base">The soul is quiet</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            No voices are flowing yet — <span className="font-mono">no_data</span>, honest silence. Once the
            field, affect and lineage speak, a determination forms here.
          </CardContent>
        </Card>
      )}

      {data && data.available && (() => {
        const s = STANCE[data.stance] ?? STANCE.wait;
        const Icon = s.icon;
        return (
          <>
            <Card>
              <CardHeader className="pb-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Icon className={`h-5 w-5 ${s.cls}`} /> {s.label}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    {data.mood && <Badge variant="outline" className="text-[10px]">{data.mood}</Badge>}
                    <Badge variant="outline" className="text-[10px]">agreement {data.agreement.toFixed(2)}</Badge>
                    <Badge variant="outline" className={`text-[10px] ${STATUS_STYLE[data.truth_status]}`}>{data.truth_status.replace("_", " ")}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm">{data.determination}</p>
                {data.what_gary_would_say && (
                  <p className="text-xs text-muted-foreground"> Gary would say: “{data.what_gary_would_say}”</p>
                )}
                {data.proposed_action && (
                  <p className="text-xs font-mono text-muted-foreground">
                    proposed: {data.proposed_action.action}
                  </p>
                )}
                {data.dissent.length > 0 && (
                  <p className="text-xs text-warning">dissent: {data.dissent.join(", ")}</p>
                )}
              </CardContent>
            </Card>

            {data.plan && data.plan.work_orders.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="text-sm">The company's directed plan</CardTitle>
                    <div className="flex items-center gap-2">
                      {data.plan.risk && <Badge variant="outline" className="text-[10px]">risk {data.plan.risk}</Badge>}
                      <Badge variant="outline" className="text-[10px]">
                        {data.plan.directed ? "directed" : "proposed — dry-run"}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  {data.plan.work_orders.map((wo) => (
                    <div key={wo.seq} className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
                      <div className="min-w-0">
                        <span className="font-medium">{wo.role}</span>
                        <span className="text-muted-foreground"> — {wo.description}</span>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="font-mono text-[10px] text-muted-foreground">{wo.action}</span>
                        {wo.outcome && (
                          <Badge variant="outline" className="text-[10px]">
                            {wo.outcome.blocked ? "blocked" : wo.outcome.dry_run ? "dry-run" : wo.outcome.executed ? "executed" : "—"}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                  <p className="text-[11px] text-muted-foreground">
                    Each step is carried out through the one guarded hand — dry-run unless armed.
                  </p>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">The chorus of voices</CardTitle></CardHeader>
              <CardContent>
                <div className="grid gap-2 sm:grid-cols-2">
                  {Object.entries(data.voices).map(([name, v]) => (
                    <div key={name} className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
                      <span className="capitalize">{name}{v.verdict ? ` · ${v.verdict}` : ""}</span>
                      <div className="flex items-center gap-2">
                        <Stance stance={v.stance} />
                        <Badge variant="outline" className={`text-[10px] ${STATUS_STYLE[(v.truth_status ?? "no_data")]}`}>
                          {(v.truth_status ?? "no_data").replace("_", " ")}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </>
        );
      })()}
    </div>
  );
}
