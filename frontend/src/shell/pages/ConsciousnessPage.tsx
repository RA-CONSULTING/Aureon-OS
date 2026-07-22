/**
 * Consciousness — the organism's inner capabilities, categorized.
 *
 * Fetches GET /api/consciousness and lays out the Phase 25-38 organs by category
 * (self-perception, selfhood, purpose, governance, the workforce, the body), each
 * with its purpose, live truth_status, safety posture, and a deep-link to its own
 * page. This is the one place that answers "what can the organism do, inside?" —
 * every irreversible move still routes to the director's desk. A dormant organ
 * shows no_data, never a fabricated capability.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Brain, ShieldCheck, ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";
import { type TruthStatus, TRUTH_STATUS_STYLE, SAFETY_POSTURE_STYLE } from "../truthStatus";


interface Surface {
  key: string;
  label: string;
  category: string;
  purpose: string;
  route: string;
  safety_posture: string;
  posture_note: string;
  available: boolean;
  truth_status: TruthStatus;
}

interface CategoryBlock {
  purpose: string;
  surface_count: number;
  surfaces: Surface[];
}

interface Axis {
  value: number | string | null;
  truth_status: TruthStatus;
  detail?: string;
}

interface StateOfBeing {
  available: boolean;
  wholeness: number | null;
  headline: string;
  axes: Record<string, Axis>;
}

interface Catalog {
  categories: Record<string, CategoryBlock>;
  surfaces: Surface[];
  state_of_being?: StateOfBeing;
  counts: {
    total: number;
    operational: number;
    category_count: number;
    by_safety_posture: Record<string, number>;
  };
  truth_status: TruthStatus;
}

const STATUS_STYLE = TRUTH_STATUS_STYLE;

const POSTURE_STYLE = SAFETY_POSTURE_STYLE;

const CATEGORY_LABEL: Record<string, string> = {
  self_perception: "Self-perception",
  selfhood: "Selfhood",
  purpose: "Purpose",
  governance: "Governance",
  workforce: "The Workforce",
  body: "The Body",
};

// The /api/* route each organ serves → its shell page (deep-link target).
const ROUTE_TO_PAGE: Record<string, string> = {
  "/api/metacognition": "/cognition/metacognition",
  "/api/affect": "/ops/affect",
  "/api/soul": "/ops/soul",
  "/api/inner-work": "/ops/inner-work",
  "/api/pursuit": "/ops/pursuit",
  "/api/approvals": "/ops/approvals",
  "/api/company": "/cognition/agents",
  "/api/organism": "/",
};

function StatusBadge({ status }: { status?: TruthStatus }) {
  const cls = STATUS_STYLE[status ?? "no_data"] ?? STATUS_STYLE.no_data;
  return <Badge variant="outline" className={`text-[10px] ${cls}`}>{(status ?? "no_data").replace(/_/g, " ")}</Badge>;
}

function PostureBadge({ posture }: { posture: string }) {
  const cls = POSTURE_STYLE[posture] ?? STATUS_STYLE.no_data;
  return <Badge variant="outline" className={`text-[10px] ${cls}`}>{posture.replace(/_/g, " ")}</Badge>;
}

function SurfaceCard({ s }: { s: Surface }) {
  const page = ROUTE_TO_PAGE[s.route] ?? null;
  const body = (
    <Card className="h-full transition-colors hover:border-primary/40">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-sm">{s.label}</CardTitle>
          <StatusBadge status={s.truth_status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">{s.purpose}</p>
        <div className="flex flex-wrap items-center gap-2">
          <PostureBadge posture={s.safety_posture} />
          <code className="text-[10px] text-muted-foreground">{s.route}</code>
          {page && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
        </div>
      </CardContent>
    </Card>
  );
  return page ? <Link to={page} className="block">{body}</Link> : body;
}

export default function ConsciousnessPage() {
  const [data, setData] = useState<Catalog | null | undefined>(undefined);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await fetch("/api/consciousness");
        if (!r.ok) throw new Error(String(r.status));
        const c: Catalog = await r.json();
        if (alive) setData(c);
      } catch {
        if (alive) setData(null);
      }
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Brain className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Consciousness</h1>
          <p className="text-sm text-muted-foreground">
            The organism's inner capabilities, categorized — what it can do inside itself, by layer.
            Read-only to inspect; every irreversible move still routes to the director's desk.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {data === undefined && (
        <div className="grid gap-3 md:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}</div>
      )}
      {data === null && (
        <Card><CardHeader><CardTitle>Gateway offline</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">Start the operator and retry — this page reads /api/consciousness.</CardContent></Card>
      )}

      {data && (
        <>
          {/* the state of being — how the organism is right now */}
          {data.state_of_being && (
            <Card className="border-primary/30">
              <CardHeader className="pb-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle className="text-base">
                    State of being
                    {data.state_of_being.wholeness != null && (
                      <span className="ml-2 font-mono text-sm text-muted-foreground">
                        wholeness {data.state_of_being.wholeness.toFixed(3)}
                      </span>
                    )}
                  </CardTitle>
                  <StatusBadge status={data.state_of_being.available ? "real_derived" : "no_data"} />
                </div>
                <p className="text-sm text-muted-foreground">{data.state_of_being.headline}</p>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {Object.entries(data.state_of_being.axes).map(([name, ax]) => (
                  <div key={name} className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs">
                    <span className="text-muted-foreground">{name.replace(/_/g, " ")}</span>
                    <span className="font-mono">
                      {ax.value == null ? "—" : typeof ax.value === "number" ? ax.value.toFixed(3) : ax.value}
                    </span>
                    <StatusBadge status={ax.truth_status} />
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* roll-up */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  {data.counts.operational}/{data.counts.total} capabilities live · {data.counts.category_count} categories
                </CardTitle>
                <StatusBadge status={data.truth_status} />
              </div>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              {Object.entries(data.counts.by_safety_posture).map(([p, n]) => (
                <span key={p} className="flex items-center gap-1"><PostureBadge posture={p} /> ×{n}</span>
              ))}
            </CardContent>
          </Card>

          {/* categories */}
          {Object.entries(data.categories).map(([name, block]) => (
            <div key={name} className="space-y-2">
              <div className="flex items-baseline gap-2">
                <h2 className="text-sm font-semibold">{CATEGORY_LABEL[name] ?? name}</h2>
                <span className="text-xs text-muted-foreground">{block.purpose}</span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {block.surfaces.map((s) => <SurfaceCard key={s.key} s={s} />)}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
