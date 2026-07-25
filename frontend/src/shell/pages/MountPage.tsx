/**
 * Aureon Mount — the OpenAI-compatible front door.
 *
 * Any flagship / AGI model mounts on Aureon by pointing its base_url here and
 * speaking POST /v1/chat/completions — the request runs *through* Aureon as the
 * host mind (grounded + vetted), and only the grounded, vetted answer comes back.
 * Reads the live self-describing manifest GET /api/mount (same-origin; the SaaS
 * gateway serves it so nginx proxies it, unlike the raw /v1 path).
 */

import { useEffect, useState } from "react";
import { Plug, Copy, ShieldCheck, Boxes } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";

interface MountEngine {
  id: string;
  engine: string;
  description: string;
}

interface MountManifest {
  service: string;
  version: string;
  summary: string;
  endpoint: string;
  models_endpoint: string;
  manifest_endpoint: string;
  engines: MountEngine[];
  default_model: string;
  request_shape: string;
  response_object: string[];
  provenance_field: string;
  provenance_keys: string[];
  boundary_behavior: string;
  human_in_the_loop: boolean;
  auth: string;
  mount_by: string;
  truth_status?: string;
}

function baseUrl(): string {
  // The mount lives at <origin>/v1 — what an integrator sets as base_url.
  if (typeof window !== "undefined" && window.location?.origin) {
    return `${window.location.origin}/v1`;
  }
  return "https://<your-aureon-host>/v1";
}

async function copy(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`${label} copied`);
  } catch {
    toast.error("Could not copy to clipboard");
  }
}

export default function MountPage() {
  // undefined = loading, null = gateway offline, object = data
  const [m, setM] = useState<MountManifest | null | undefined>(undefined);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch("/api/mount");
        if (!r.ok) throw new Error(String(r.status));
        setM((await r.json()) as MountManifest);
      } catch {
        setM(null);
      }
    })();
  }, []);

  const base = baseUrl();
  const curl =
    `curl -s ${base}/chat/completions \\\n` +
    `  -H "Authorization: Bearer $AUREON_OPERATOR_API_KEY" \\\n` +
    `  -H "Content-Type: application/json" \\\n` +
    `  -d '{"model":"aureon-cognition","messages":[{"role":"user","content":"How does Aureon ground its answers?"}]}'`;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Plug className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Aureon Mount</h1>
          <p className="text-sm text-muted-foreground">
            The OpenAI-compatible front door. Point any model client's base URL here — every request
            runs through Aureon as the host mind: grounded, vetted, human-in-the-loop.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {m === undefined && (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      )}

      {m === null && (
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

      {m && typeof m === "object" && (
        <>
          {/* Mount by — the base_url swap + a ready curl */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-lg">Mount in one line</CardTitle>
                <div className="flex items-center gap-2">
                  {m.human_in_the_loop && (
                    <Badge variant="secondary" className="gap-1">
                      <ShieldCheck className="h-3.5 w-3.5" /> human-in-the-loop
                    </Badge>
                  )}
                  {m.truth_status && <Badge className="bg-emerald-600 hover:bg-emerald-600">live</Badge>}
                </div>
              </div>
              <CardDescription>{m.summary}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-muted-foreground">Base URL</div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 truncate rounded bg-muted px-3 py-2 text-sm">{base}</code>
                  <Button type="button" variant="outline" size="icon" onClick={() => copy(base, "Base URL")}>
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">{m.mount_by}</p>
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-medium text-muted-foreground">Try it</div>
                  <Button type="button" variant="ghost" size="sm" onClick={() => copy(curl, "curl")}>
                    <Copy className="mr-1 h-3.5 w-3.5" /> copy
                  </Button>
                </div>
                <pre className="overflow-x-auto rounded bg-muted px-3 py-2 text-xs leading-relaxed">
                  {curl}
                </pre>
              </div>
            </CardContent>
          </Card>

          {/* Engines */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Boxes className="h-4 w-4" /> Engines — pick one with the <code>model</code> field
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {m.engines.map((e) => (
                <Card key={e.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="text-base">
                        <code>{e.id}</code>
                      </CardTitle>
                      {e.id === m.default_model && <Badge variant="secondary">default</Badge>}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{e.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* The contract */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">The contract</CardTitle>
              <CardDescription>What every mounted response guarantees.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <div className="text-xs font-medium text-muted-foreground">Endpoint</div>
                <code className="text-sm">{m.endpoint}</code>
              </div>
              <div>
                <div className="text-xs font-medium text-muted-foreground">Request</div>
                <span>{m.request_shape}</span>
              </div>
              <div>
                <div className="text-xs font-medium text-muted-foreground">Response</div>
                <span>{m.response_object.join(" · ")}</span>
              </div>
              <div>
                <div className="text-xs font-medium text-muted-foreground">Auth</div>
                <span>{m.auth}</span>
              </div>
              <div className="sm:col-span-2">
                <div className="text-xs font-medium text-muted-foreground">
                  Provenance — every reply carries an additive <code>{m.provenance_field}</code> block
                </div>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {m.provenance_keys.map((k) => (
                    <Badge key={k} variant="outline" className="font-mono text-[11px]">
                      {k}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="sm:col-span-2">
                <div className="text-xs font-medium text-muted-foreground">Safety boundary</div>
                <p className="text-muted-foreground">{m.boundary_behavior}</p>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
