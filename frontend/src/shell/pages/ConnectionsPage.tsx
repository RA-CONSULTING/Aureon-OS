/**
 * Connections — every external source, in one view.
 *
 * Trading exchanges → market data → NASA/space weather → on-chain/whale → news →
 * notifications, plus the AI/LLM models. Shows a "full operational capacity"
 * readiness banner, then per-category rows with a status dot, a connectivity
 * Test, and inline key entry. Exchange keys are delegated to the trader's .env
 * writer; keyless feeds get a reachability test only. Keys are masked; the raw
 * value only travels on Save/Test. Reads GET /api/connections(+/readiness);
 * writes POST /api/connections/<id>(+/test).
 */

import { useEffect, useState } from "react";
import { Radar, Eye, EyeOff, Loader2, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";

interface Conn {
  id: string;
  label: string;
  category: string;
  requirement: "required" | "optional" | "keyless";
  consumed_by?: string;
  has_key: boolean;
  key_masked: string;
  key_source?: string;
  enabled: boolean;
  connected?: boolean | null;
  runtime_ready?: boolean | null;
  unlocks?: string;
  get_keys_url?: string;
  docs_url?: string;
  has_probe?: boolean;
  extra_envs?: string[];
  secondary_labels?: string[];
  notes?: string;
}
interface Section { category: string; label: string; connections: Conn[]; }
interface Readiness {
  summary: {
    capacity_pct: number; keyed_present: number; keyed_total: number;
    keyless: number; all_connected: boolean; missing_count: number;
  };
  missing: { id: string; label: string; category: string; unlocks: string; get_keys_url: string }[];
}
interface Draft { apiKey: string; extra: Record<string, string>; show: boolean; testing: boolean; saving: boolean; }

export default function ConnectionsPage() {
  const [sections, setSections] = useState<Section[] | null | undefined>(undefined);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [showMissing, setShowMissing] = useState(false);

  async function load() {
    try {
      const [c, r] = await Promise.all([
        fetch("/api/connections").then((x) => (x.ok ? x.json() : Promise.reject())),
        fetch("/api/connections/readiness").then((x) => (x.ok ? x.json() : null)).catch(() => null),
      ]);
      setSections(c.categories ?? []);
      setReadiness(r);
    } catch {
      setSections(null);
    }
  }
  useEffect(() => { load(); }, []);

  const draft = (c: Conn): Draft => drafts[c.id] ?? { apiKey: "", extra: {}, show: false, testing: false, saving: false };
  const patch = (id: string, f: Partial<Draft>) =>
    setDrafts((d) => ({ ...d, [id]: { ...draft({ id } as Conn), ...d[id], ...f } }));

  function body(c: Conn) {
    const d = draft(c);
    const b: Record<string, unknown> = {};
    if (d.apiKey.trim()) b.api_key = d.apiKey.trim();
    if (c.extra_envs?.length && Object.keys(d.extra).length) b.extra = d.extra;
    return b;
  }

  async function save(c: Conn) {
    patch(c.id, { saving: true });
    try {
      const r = await fetch(`/api/connections/${c.id}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body(c)),
      });
      const v = await r.json();
      if (!r.ok || v.ok === false) throw new Error(v.error || String(r.status));
      toast.success(`${c.label} saved`, {
        description: c.category === "exchange" ? "written to .env — trader picks it up on restart" : undefined,
      });
      patch(c.id, { apiKey: "", extra: {} });
      await load();
    } catch (e) {
      toast.error(`Could not save ${c.label}`, { description: e instanceof Error ? e.message : undefined });
    } finally {
      patch(c.id, { saving: false });
    }
  }

  async function test(c: Conn) {
    patch(c.id, { testing: true });
    try {
      const r = await fetch(`/api/connections/${c.id}/test`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body(c)),
      });
      const v = await r.json();
      if (v.ok) toast.success(`${c.label} reachable`, { description: v.latency_ms ? `${v.latency_ms} ms` : undefined });
      else toast.error(`${c.label} test failed`, { description: v.error });
    } catch {
      toast.error(`${c.label} test failed`, { description: "gateway unreachable" });
    } finally {
      patch(c.id, { testing: false });
    }
  }

  function dot(c: Conn) {
    const live = c.connected === true || c.runtime_ready === true;
    const color = live ? "bg-emerald-500" : c.requirement === "keyless" ? "bg-sky-500" : c.has_key ? "bg-amber-500" : "bg-muted-foreground/40";
    const title = live ? "connected" : c.requirement === "keyless" ? "keyless / public" : c.has_key ? "key set" : "needs key";
    return <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} title={title} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Radar className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Connections</h1>
          <p className="text-sm text-muted-foreground">
            Every external source Aureon uses — from trading exchanges to NASA — with keys, live
            status, and what it takes to run at full operational capacity.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {/* Readiness banner */}
      {readiness && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="text-base">
                Full operational capacity: {readiness.summary.capacity_pct}%
              </CardTitle>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Badge variant={readiness.summary.all_connected ? "default" : "secondary"}>
                  {readiness.summary.keyed_present}/{readiness.summary.keyed_total} keyed connected
                </Badge>
                <Badge variant="outline">{readiness.summary.keyless} keyless feeds</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-primary transition-all" style={{ width: `${readiness.summary.capacity_pct}%` }} />
            </div>
            {readiness.summary.missing_count > 0 && (
              <button className="text-xs text-primary hover:underline" onClick={() => setShowMissing((s) => !s)}>
                {readiness.summary.missing_count} sources need a key — {showMissing ? "hide" : "show"}
              </button>
            )}
            {showMissing && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {readiness.missing.map((m) => (
                  <a key={m.id} href={m.get_keys_url} target="_blank" rel="noopener noreferrer"
                     className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground hover:border-primary hover:text-primary"
                     title={m.unlocks}>{m.label}</a>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {sections === undefined && (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 w-full" />)}</div>
      )}
      {sections === null && (
        <Card><CardHeader><CardTitle>Gateway offline</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">Start the operator and retry.</CardContent></Card>
      )}

      {Array.isArray(sections) && sections.map((sec) => sec.connections.length > 0 && (
        <div key={sec.category} className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{sec.label}</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {sec.connections.map((c) => {
              const d = draft(c);
              const keyed = c.requirement !== "keyless";
              return (
                <Card key={c.id} className="flex flex-col">
                  <CardContent className="flex flex-1 flex-col gap-2 pt-4">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">{dot(c)}<span className="font-medium">{c.label}</span></div>
                      {c.has_key && keyed && <Badge variant="outline" className="text-[10px]">{c.key_masked} · {c.key_source}</Badge>}
                      {c.requirement === "keyless" && <Badge variant="outline" className="text-[10px]">keyless</Badge>}
                    </div>
                    {c.unlocks && <p className="text-xs text-muted-foreground">{c.unlocks}</p>}

                    {keyed && (
                      <div className="flex gap-2">
                        <Input
                          type={d.show ? "text" : "password"}
                          aria-label={`${c.label} API key`}
                          placeholder={c.has_key ? "•••• (leave blank to keep)" : "paste key"}
                          value={d.apiKey} autoComplete="off"
                          onChange={(e) => patch(c.id, { apiKey: e.target.value })}
                        />
                        <Button type="button" variant="outline" size="icon"
                          onClick={() => patch(c.id, { show: !d.show })} aria-label="toggle">
                          {d.show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                    )}
                    {keyed && (c.extra_envs ?? []).map((env, i) => (
                      <Input key={env} placeholder={c.secondary_labels?.[i] ?? env}
                        aria-label={c.secondary_labels?.[i] ?? env}
                        value={d.extra[env] ?? ""} autoComplete="off"
                        onChange={(e) => patch(c.id, { extra: { ...d.extra, [env]: e.target.value } })} />
                    ))}
                    {c.category === "exchange" && (
                      <p className="text-[11px] text-warning">Saved to .env — the trading process applies it on restart.</p>
                    )}

                    <div className="mt-auto flex items-center justify-between pt-1">
                      <div className="flex gap-3 text-xs">
                        {c.get_keys_url && <a className="inline-flex items-center gap-1 text-primary hover:underline" href={c.get_keys_url} target="_blank" rel="noopener noreferrer">Get key <ExternalLink className="h-3 w-3" /></a>}
                        {c.docs_url && <a className="inline-flex items-center gap-1 text-muted-foreground hover:underline" href={c.docs_url} target="_blank" rel="noopener noreferrer">Docs</a>}
                      </div>
                      <div className="flex gap-2">
                        {(c.has_probe || c.category === "ai_llm") && (
                          <Button type="button" variant="outline" size="sm" disabled={d.testing} onClick={() => test(c)}>
                            {d.testing && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}Test
                          </Button>
                        )}
                        {keyed && (
                          <Button type="button" size="sm" disabled={d.saving} onClick={() => save(c)}>
                            {d.saving && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}Save
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
