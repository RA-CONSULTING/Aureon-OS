import { useEffect, useState } from "react";
import { BrainCircuit, GitBranch, Hammer, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

type JsonMap = Record<string, any>;

async function fetchJson(url: string): Promise<JsonMap> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return {};
    return await response.json();
  } catch {
    return {};
  }
}

function fmt(value: unknown): string {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toLocaleString() : String(value || "0");
}

export function AureonDirectorCapabilityBridgeConsole() {
  const [report, setReport] = useState<JsonMap>({});

  useEffect(() => {
    const refresh = async () => setReport(await fetchJson("/aureon_director_capability_bridge.json"));
    refresh();
    const timer = window.setInterval(refresh, 20000);
    return () => window.clearInterval(timer);
  }, []);

  const summary = report.summary || {};
  const rows = Array.isArray(report.codex_class_capabilities) ? report.codex_class_capabilities : [];
  const orders = Array.isArray(report.aureon_bridge_work_orders) ? report.aureon_bridge_work_orders : [];

  return (
    <Card className="mb-5 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <BrainCircuit className="h-4 w-4 text-primary" />
          Aureon Director Capability Bridge
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant={summary.gap_count ? "warning" : "success"}>{report.status || "waiting"}</Badge>
          <Badge variant="outline">coverage {fmt(summary.coverage_percent)}%</Badge>
          <Badge variant="outline">work orders {fmt(summary.bridge_work_order_count)}</Badge>
          <Badge variant="outline">updated {report.generated_at ? new Date(report.generated_at).toLocaleTimeString() : "pending"}</Badge>
        </div>

        <div className="grid gap-2 md:grid-cols-4">
          <Metric icon={ShieldCheck} label="ready" value={summary.ready_count || 0} />
          <Metric icon={Hammer} label="partial" value={summary.partial_count || 0} />
          <Metric icon={GitBranch} label="gaps" value={summary.gap_count || 0} />
          <Metric icon={BrainCircuit} label="capabilities" value={summary.capability_count || 0} />
        </div>

        <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
          <ScrollArea className="h-[340px] pr-3">
            <div className="space-y-2">
              {rows.map((row: JsonMap) => (
                <div key={row.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium">{row.title}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{row.codex_can}</div>
                    </div>
                    <Badge variant={row.status === "ready" ? "success" : row.status === "gap" ? "warning" : "outline"}>
                      {row.status}
                    </Badge>
                  </div>
                  <div className="mt-2 truncate font-mono text-[10px] text-muted-foreground">
                    {(row.blockers || []).join(" | ") || "all required surfaces present"}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          <ScrollArea className="h-[340px] pr-3">
            <div className="space-y-2">
              {orders.map((order: JsonMap) => (
                <div key={order.id} className="rounded-md border border-warning/30 bg-warning/10 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="text-sm font-medium">{order.title}</div>
                    <Badge variant="outline">P{order.priority}</Badge>
                  </div>
                  <div className="mt-2 text-xs text-warning">{order.exact_aureon_prompt}</div>
                  <div className="mt-2 truncate font-mono text-[10px] text-muted-foreground">{order.route}</div>
                </div>
              ))}
              {!orders.length ? (
                <div className="rounded-md border border-success/30 bg-success/10 p-4 text-sm text-success">
                  No bridge gaps detected.
                </div>
              ) : null}
            </div>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ icon: Icon, label, value }: { icon: any; label: string; value: unknown }) {
  return (
    <div className="rounded-md border border-border/40 bg-muted/10 p-3">
      <div className="flex items-center gap-2 text-[11px] uppercase text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold">{fmt(value)}</div>
    </div>
  );
}
