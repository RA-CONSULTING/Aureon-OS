/**
 * Cognitive Systems — the organism's substrate as verified SaaS.
 *
 * Reads GET /api/cognition and renders the five cognitive + meta-cognitive
 * surfaces (HNC field · thought-bus links · mycelium mesh · connectome body-map ·
 * miner brain), each with an honest data-provenance badge (live / real_derived /
 * cached_real / no_data). A dormant organ shows as no_data — never a fabricated
 * value. The provenance header reflects the repo's real-data contract.
 */

import { useEffect, useState } from "react";
import { Brain, Radio, Network, Waypoints, Activity, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";
import { type TruthStatus, TRUTH_STATUS_STYLE } from "../truthStatus";


interface Surface {
  truth_status: TruthStatus;
  blocker?: string;
  [k: string]: unknown;
}

interface CognitivePayload {
  available: boolean;
  product_domain: string;
  surfaces: Record<string, Surface>;
  registry: { surface: string; accessor: string; note: string; available: boolean }[];
  provenance: {
    simulation_fallback_allowed: boolean;
    truth_statuses: string[];
    source_registry_count: number;
    policy?: string;
  };
  truth_summary: Record<string, number>;
  operational_ready: number;
  blocked: number;
}

const SURFACE_META: Record<string, { label: string; icon: typeof Brain; blurb: string }> = {
  field: { label: "HNC Field", icon: Radio, blurb: "The shared coherence — canonical reading, sub-fields, and the blended whole-body consensus." },
  bus: { label: "Thought-Bus Links", icon: Waypoints, blurb: "The living topology — which cognitive topic families carry signal and who listens." },
  mycelium: { label: "Mycelium Mesh", icon: Network, blurb: "Mesh coherence, hives, agents, and connected systems (reported only when the mesh is running here)." },
  connectome: { label: "Connectome Body-Map", icon: Activity, blurb: "How much of the 715-module body the organism has actually felt — linked, touched, woven." },
  brain: { label: "Miner Brain", icon: BookOpen, blurb: "Prediction accuracy and knowledge memory, read from persisted state (the brain is never woken)." },
};

const STATUS_STYLE: Record<TruthStatus, { cls: string; label: string }> = {
  live: { cls: TRUTH_STATUS_STYLE.live, label: "live" },
  real_derived: { cls: TRUTH_STATUS_STYLE.real_derived, label: "real · derived" },
  cached_real: { cls: TRUTH_STATUS_STYLE.cached_real, label: "cached real" },
  no_data: { cls: TRUTH_STATUS_STYLE.no_data, label: "no data" },
  test_fixture: { cls: TRUTH_STATUS_STYLE.test_fixture, label: "test fixture" },
};

function StatusBadge({ status }: { status: TruthStatus }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.no_data;
  return <Badge variant="outline" className={`text-[10px] ${s.cls}`}>{s.label}</Badge>;
}

/** Render the human-relevant fields of one surface without leaking internals. */
function surfaceDetail(name: string, s: Surface): { label: string; value: string }[] {
  const rows: { label: string; value: string }[] = [];
  const num = (v: unknown) => (typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(3)) : "—");
  if (name === "field") {
    const canonical = (s.canonical ?? {}) as Record<string, unknown>;
    const blended = (s.blended ?? {}) as Record<string, unknown>;
    const subs = (s.subfields ?? {}) as Record<string, unknown>;
    rows.push({ label: "symbolic life", value: num(canonical.symbolic_life_score) });
    rows.push({ label: "coherence γ", value: num(canonical.coherence_gamma) });
    rows.push({ label: "sub-fields", value: num(subs.count) });
    rows.push({ label: "blended contributors", value: num(blended.contributors) });
  } else if (name === "bus") {
    rows.push({ label: "subscribed topics", value: num(s.subscribed_topic_count) });
    rows.push({ label: "total subscribers", value: num(s.total_subscribers) });
    rows.push({ label: "cognitive links flowing", value: num(s.cognitive_links_flowing) });
  } else if (name === "mycelium") {
    rows.push({ label: "coherence", value: num(s.coherence) });
    rows.push({ label: "hives", value: num(s.hive_count) });
    rows.push({ label: "agents", value: num(s.agent_count) });
    rows.push({ label: "connected systems", value: num(s.connected_count) });
  } else if (name === "connectome") {
    const map = (s.body_map ?? {}) as Record<string, unknown>;
    rows.push({ label: "nodes", value: num(map.nodes) });
    rows.push({ label: "baton linked", value: num(map.baton_linked) });
    rows.push({ label: "woven", value: num(map.woven) });
    rows.push({ label: "coverage", value: map.coverage_pct != null ? `${num(map.coverage_pct)}%` : "—" });
  } else if (name === "brain") {
    const acc = (s.accuracy ?? {}) as Record<string, unknown>;
    const know = (s.knowledge ?? {}) as Record<string, unknown>;
    rows.push({ label: "predictions", value: num(acc.total_predictions) });
    rows.push({ label: "validated", value: num(acc.validated) });
    rows.push({ label: "accuracy", value: acc.accuracy_pct != null ? `${num(acc.accuracy_pct)}%` : "—" });
    rows.push({ label: "knowledge entries", value: num(know.entries) });
  }
  return rows;
}

export default function CognitivePage() {
  const [data, setData] = useState<CognitivePayload | null | undefined>(undefined);

  useEffect(() => {
    fetch("/api/cognition")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => setData(null));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Brain className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Cognitive Systems</h1>
          <p className="text-sm text-muted-foreground">
            The organism's cognitive and meta-cognitive substrate — field, bus, mycelium, connectome,
            and brain — as verified read APIs. Every surface is stamped with honest data provenance.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {data === undefined && (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-36 w-full" />)}</div>
      )}
      {data === null && (
        <Card><CardHeader><CardTitle>Gateway offline</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">Start the operator and retry.</CardContent></Card>
      )}

      {data && (
        <>
          {/* Provenance + truth roll-up */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="text-base">
                  {data.operational_ready} of {data.operational_ready + data.blocked} surfaces verified
                </CardTitle>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Badge variant={data.blocked === 0 ? "default" : "secondary"}>
                    {data.operational_ready} operational
                  </Badge>
                  {data.blocked > 0 && <Badge variant="outline">{data.blocked} blocked</Badge>}
                  <Badge variant="outline" className="text-[10px]">
                    sim fallback: {data.provenance.simulation_fallback_allowed ? "allowed" : "off"}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              {data.provenance.policy} · {data.provenance.source_registry_count} registered real-data sources.
            </CardContent>
          </Card>

          {/* One card per surface */}
          <div className="grid gap-3 md:grid-cols-2">
            {Object.entries(data.surfaces).map(([name, surface]) => {
              const meta = SURFACE_META[name] ?? { label: name, icon: Brain, blurb: "" };
              const Icon = meta.icon;
              return (
                <Card key={name} className="flex flex-col">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-primary" />
                        <CardTitle className="text-sm">{meta.label}</CardTitle>
                      </div>
                      <StatusBadge status={surface.truth_status} />
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-1 flex-col gap-2">
                    <p className="text-xs text-muted-foreground">{meta.blurb}</p>
                    {surface.truth_status === "no_data" ? (
                      <p className="mt-auto text-xs italic text-muted-foreground">{surface.blocker ?? "no data"}</p>
                    ) : (
                      <dl className="mt-auto grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                        {surfaceDetail(name, surface).map((row) => (
                          <div key={row.label} className="flex justify-between gap-2">
                            <dt className="text-muted-foreground">{row.label}</dt>
                            <dd className="font-mono">{row.value}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
