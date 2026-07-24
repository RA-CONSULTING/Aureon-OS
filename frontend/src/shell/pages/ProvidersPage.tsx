/**
 * Providers — LLM API-key management.
 *
 * Bring your own key for every model (OpenAI, Anthropic/Claude, xAI/Grok,
 * Gemini, Ollama, DeepSeek, Mistral, Groq, OpenRouter, Perplexity). Keys are
 * stored encrypted on the server (never returned in full — only masked), and
 * saving hot-reloads the switchboard. Reads GET /api/providers; writes
 * POST/DELETE /api/providers/<id> and POST /api/providers/<id>/test.
 */

import { useEffect, useState } from "react";
import { KeyRound, Eye, EyeOff, Loader2, CheckCircle2, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";

interface Provider {
  id: string;
  label: string;
  kind: string;
  default_model: string;
  default_base_url: string;
  get_keys_url: string;
  docs_url: string;
  key_optional: boolean;
  notes: string;
  model: string;
  base_url: string;
  has_key: boolean;
  key_masked: string;
  key_source: "keystore" | "env" | "none";
  enabled: boolean;
  live: boolean;
}

interface Draft {
  apiKey: string;
  model: string;
  baseUrl: string;
  show: boolean;
  testing: boolean;
  saving: boolean;
}

const emptyDraft = (p: Provider): Draft => ({
  apiKey: "",
  model: p.model || p.default_model,
  baseUrl: p.base_url || p.default_base_url,
  show: false,
  testing: false,
  saving: false,
});

export default function ProvidersPage() {
  // undefined = loading, null = gateway offline, array = data
  const [providers, setProviders] = useState<Provider[] | null | undefined>(undefined);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});

  async function load() {
    try {
      const r = await fetch("/api/providers");
      if (!r.ok) throw new Error(String(r.status));
      const data = await r.json();
      const list: Provider[] = data.providers ?? [];
      setProviders(list);
      setDrafts((prev) => {
        const next = { ...prev };
        for (const p of list) if (!next[p.id]) next[p.id] = emptyDraft(p);
        return next;
      });
    } catch {
      setProviders(null);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const patch = (id: string, fields: Partial<Draft>) =>
    setDrafts((d) => ({ ...d, [id]: { ...d[id], ...fields } }));

  async function save(p: Provider, extra?: Partial<{ enabled: boolean }>) {
    const d = drafts[p.id];
    patch(p.id, { saving: true });
    try {
      const body: Record<string, unknown> = { model: d.model, base_url: d.baseUrl, ...extra };
      if (d.apiKey.trim()) body.api_key = d.apiKey.trim();
      const r = await fetch(`/api/providers/${p.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(String(r.status));
      toast.success(`${p.label} saved`);
      patch(p.id, { apiKey: "" }); // never keep the raw key in the field
      await load();
    } catch {
      toast.error(`Could not save ${p.label}`);
    } finally {
      patch(p.id, { saving: false });
    }
  }

  async function test(p: Provider) {
    const d = drafts[p.id];
    patch(p.id, { testing: true });
    try {
      const body: Record<string, unknown> = { model: d.model, base_url: d.baseUrl };
      if (d.apiKey.trim()) body.api_key = d.apiKey.trim();
      const r = await fetch(`/api/providers/${p.id}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const v = await r.json();
      if (v.ok) toast.success(`${p.label} responded in ${v.latency_ms} ms`, { description: v.sample });
      else toast.error(`${p.label} test failed`, { description: v.error });
    } catch {
      toast.error(`${p.label} test failed`, { description: "gateway unreachable" });
    } finally {
      patch(p.id, { testing: false });
    }
  }

  async function clearKey(p: Provider) {
    try {
      const r = await fetch(`/api/providers/${p.id}`, { method: "DELETE" });
      if (!r.ok) throw new Error(String(r.status));
      toast.success(`${p.label} cleared`);
      await load();
    } catch {
      toast.error(`Could not clear ${p.label}`);
    }
  }

  function statusBadge(p: Provider) {
    if (p.live) return <Badge className="bg-success hover:bg-success">live</Badge>;
    if (p.has_key) return <Badge variant="secondary">key set · idle</Badge>;
    return <Badge variant="outline">needs key</Badge>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <KeyRound className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Providers</h1>
          <p className="text-sm text-muted-foreground">
            Bring your own API key for every model. Keys are encrypted on the server, shown only
            masked, and never leave the box. Saving reloads the switchboard live.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {providers === undefined && (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-56 w-full" />
          ))}
        </div>
      )}

      {providers === null && (
        <Card>
          <CardHeader>
            <CardTitle>Gateway offline</CardTitle>
            <CardDescription>
              The operator API is not reachable. Start the operator (or open the deployed URL) and
              retry.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {Array.isArray(providers) && (
        <div className="grid gap-4 md:grid-cols-2">
          {providers.map((p) => {
            const d = drafts[p.id] ?? emptyDraft(p);
            return (
              <Card key={p.id} className="flex flex-col">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-lg">{p.label}</CardTitle>
                    <div className="flex items-center gap-2">
                      {statusBadge(p)}
                      <Switch
                        checked={p.enabled}
                        onCheckedChange={(v) => save(p, { enabled: v })}
                        aria-label={`Enable ${p.label}`}
                      />
                    </div>
                  </div>
                  <CardDescription>
                    {p.has_key ? (
                      <span className="inline-flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                        key {p.key_masked} ({p.key_source})
                      </span>
                    ) : (
                      p.notes || "No key set."
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor={`key-${p.id}`}>
                      API key{p.key_optional ? " (optional for local)" : ""}
                    </Label>
                    <div className="flex gap-2">
                      <Input
                        id={`key-${p.id}`}
                        type={d.show ? "text" : "password"}
                        placeholder={p.has_key ? "•••• (leave blank to keep)" : "paste key"}
                        value={d.apiKey}
                        autoComplete="off"
                        onChange={(e) => patch(p.id, { apiKey: e.target.value })}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={() => patch(p.id, { show: !d.show })}
                        aria-label={d.show ? "Hide key" : "Show key"}
                      >
                        {d.show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1.5">
                      <Label htmlFor={`model-${p.id}`}>Model</Label>
                      <Input
                        id={`model-${p.id}`}
                        value={d.model}
                        onChange={(e) => patch(p.id, { model: e.target.value })}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor={`url-${p.id}`}>Base URL</Label>
                      <Input
                        id={`url-${p.id}`}
                        value={d.baseUrl}
                        placeholder={p.default_base_url}
                        onChange={(e) => patch(p.id, { baseUrl: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="mt-auto flex items-center justify-between pt-2">
                    <div className="flex gap-3 text-xs">
                      <a
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                        href={p.get_keys_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Get key <ExternalLink className="h-3 w-3" />
                      </a>
                      <a
                        className="inline-flex items-center gap-1 text-muted-foreground hover:underline"
                        href={p.docs_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Docs <ExternalLink className="h-3 w-3" />
                      </a>
                      {p.has_key && (
                        <button
                          type="button"
                          className="text-muted-foreground hover:text-destructive hover:underline"
                          onClick={() => clearKey(p)}
                        >
                          Clear
                        </button>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={d.testing}
                        onClick={() => test(p)}
                      >
                        {d.testing && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
                        Test
                      </Button>
                      <Button type="button" size="sm" disabled={d.saving} onClick={() => save(p)}>
                        {d.saving && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
                        Save
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
