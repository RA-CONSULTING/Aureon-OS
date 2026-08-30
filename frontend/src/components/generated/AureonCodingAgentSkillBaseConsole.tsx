import { useEffect, useMemo, useState, type ReactNode } from "react";
import { BrainCircuit, Code2, Globe2, SearchCheck, ShieldCheck, UsersRound } from "lucide-react";
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

export function AureonCodingAgentSkillBaseConsole() {
  const [profile, setProfile] = useState<JsonMap>({});

  useEffect(() => {
    let cancelled = false;
    fetchJson("/aureon_coding_agent_skill_base.json").then((payload) => {
      if (!cancelled) setProfile(payload);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const summary = profile.summary || {};
  const agents = Array.isArray(profile.coder_agents) ? profile.coder_agents : [];
  const orders = Array.isArray(profile.coding_work_orders) ? profile.coding_work_orders : [];
  const tools = profile.tool_registry || {};
  const repoCode = profile.repo_code || {};
  const domains = repoCode.by_domain || {};
  const languages = repoCode.by_language || {};
  const logicMap = profile.coding_logic_map || {};
  const logicRules = Array.isArray(logicMap.rules) ? logicMap.rules : [];
  const sources = Array.isArray(profile.official_learning_sources) ? profile.official_learning_sources : [];
  const visibleOrders = useMemo(() => orders.slice(0, 30), [orders]);

  return (
    <Card className="mb-5 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <BrainCircuit className="h-4 w-4 text-primary" />
          Aureon Coding Agent Skill Base
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="border-success/40 bg-success/10 text-success">{profile.status || "pending"}</Badge>
          <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">updated {profile.generated_at ? new Date(profile.generated_at).toLocaleTimeString() : "pending"}</Badge>
          <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary">web tools {summary.web_tools_ready ? "ready" : "attention"}</Badge>
          <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary">{logicMap.status || "logic pending"}</Badge>
        </div>
        <div className="grid gap-2 md:grid-cols-6">
          <Stat icon={UsersRound} label="coder agents" value={summary.coder_agent_count} />
          <Stat icon={Code2} label="repo files" value={repoCode.file_count} />
          <Stat icon={BrainCircuit} label="skills" value={summary.skill_count} />
          <Stat icon={Globe2} label="learning sources" value={sources.length} />
          <Stat icon={ShieldCheck} label="logic rules" value={logicRules.length} />
          <Stat icon={SearchCheck} label="work orders" value={orders.length} />
        </div>
        <div className="grid gap-3 lg:grid-cols-3">
          <Panel title="Agents">
            {agents.slice(0, 6).map((agent: JsonMap) => (
              <div key={agent.name} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="text-sm font-medium">{agent.name}</div>
                <div className="mt-1 text-xs text-muted-foreground">{agent.purpose}</div>
              </div>
            ))}
          </Panel>
          <Panel title="Skill And Tool State">
            <Mini label="In-house tools" value={tools.inhouse_tool_count} />
            <Mini label="Missing coder tools" value={(tools.missing_required_coder_tools || []).length} />
            <Mini label="Languages" value={Object.keys(languages).length} />
            <Mini label="Domains" value={Object.keys(domains).length} />
          </Panel>
          <Panel title="Learning Sources">
            {sources.slice(0, 7).map((source: JsonMap) => (
              <div key={source.id} className="rounded-md border border-border/40 bg-muted/10 p-2">
                <div className="text-xs font-medium">{source.title}</div>
                <div className="truncate font-mono text-[10px] text-muted-foreground">{source.url}</div>
              </div>
            ))}
          </Panel>
        </div>
        <Panel title="Who What Where When How">
          <div className="text-xs text-muted-foreground">{logicMap.principle || "Coding route pending."}</div>
          <div className="grid gap-2 lg:grid-cols-2">
            {logicRules.slice(0, 6).map((rule: JsonMap) => (
              <div key={rule.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-medium">{rule.id}</div>
                  <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">{(rule.who || []).slice(0, 2).join(" + ")}</Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">{rule.what}</div>
                <div className="mt-2 truncate font-mono text-[10px] text-success">{(rule.where || []).slice(0, 3).join(" | ")}</div>
              </div>
            ))}
          </div>
        </Panel>
        <ScrollArea className="h-[320px] pr-3">
          <div className="space-y-2">
            {visibleOrders.map((order: JsonMap) => (
              <div key={order.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium">{order.title}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{order.reason}</div>
                  </div>
                  <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">{order.owner_agent}</Badge>
                </div>
                <div className="mt-2 text-xs text-success">{order.proposed_action}</div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function Stat({ icon: Icon, label, value }: { icon: any; label: string; value: unknown }) {
  return (
    <div className="rounded-md border border-border/40 bg-muted/10 p-3">
      <div className="flex items-center gap-2 text-[11px] uppercase text-muted-foreground"><Icon className="h-3.5 w-3.5" />{label}</div>
      <div className="mt-1 text-lg font-semibold">{fmt(value)}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-2 rounded-md border border-border/40 bg-muted/10 p-3">
      <div className="flex items-center gap-2 text-sm font-medium"><ShieldCheck className="h-4 w-4 text-primary" />{title}</div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Mini({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border/30 bg-background/20 px-3 py-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-semibold">{fmt(value)}</span>
    </div>
  );
}
