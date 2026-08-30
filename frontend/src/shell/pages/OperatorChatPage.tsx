/**
 * Operator Chat — talk to the grounded Aureon cognition.
 *
 * POSTs to the gateway's /api/cognition/reason (through the nginx /api proxy)
 * and renders the full provenance honestly: repo grounding sources, tool calls,
 * the conscience verdict, and blocks. No backend → a clear offline notice.
 */

import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Brain, KeyRound, Send, ShieldAlert, ShieldCheck, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/services/apiClient";
import { useSetupStatus } from "@/hooks/useSetupStatus";
import { LiveDataNotice } from "../Page";

interface GroundingSource {
  title?: string;
  path?: string;
  score?: string;
}

interface ResponseEnvelope {
  status?: string;
  sources_statement?: string;
  capability?: { families?: string[]; complex?: boolean };
  coherence?: { lead_family?: string; gamma_by_cluster?: Record<string, number | null> } | null;
  actualization?: { realized_count?: number; parked_count?: number; answer?: string } | null;
  bake?: { passes?: number; complete?: boolean | null; refined?: boolean } | null;
  knowledge_reach?: string[];
  acquisition?: { triggered?: boolean; outcome?: string } | null;
  coherence_gate?: { aperture?: string; field_status?: string } | null;
  heart?: {
    alive?: { symbolic_life_score?: number | null; status?: string };
    love?: { love_amplitude?: number | null; mood?: string | null; status?: string };
    power?: { withheld?: string[]; statement?: string };
  } | null;
}

interface CognitionReply {
  text?: string;
  grounded?: boolean;
  blocked?: boolean;
  conscience_verdict?: string;
  conscience_message?: string;
  turns?: number;
  elapsed_ms?: number;
  grounding?: { sources?: GroundingSource[] } | null;
  tool_calls?: Array<{ tool?: string; name?: string }>;
  trace_id?: string;
  envelope?: ResponseEnvelope | null;
}

interface ChatTurn {
  role: "user" | "aureon" | "error";
  text: string;
  reply?: CognitionReply;
}

const SUGGESTIONS = [
  "How does Aureon ground its answers in the repo?",
  "Explain the Master Formula Λ(t) in plain language.",
  "What does the current platform status mean?",
  "How do I run the operator gateway locally?",
];

export default function OperatorChatPage() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const setup = useSetupStatus();
  // Gateway reachable but no model connected → guide the user instead of failing at send time.
  const needsKey = !setup.loading && !setup.offline && !setup.hasProvider;

  const ask = async (prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed || busy) return;
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { role: "user", text: trimmed }]);
    try {
      // Reasoning can take a while; allow a generous timeout. apiClient attaches the
      // end-user session bearer when one exists (tenant identity).
      const reply = await api.post<CognitionReply>(
        "/api/cognition/reason",
        { prompt: trimmed },
        { timeoutMs: 60000 },
      );
      setTurns((t) => [...t, { role: "aureon", text: reply.text || "(empty answer)", reply }]);
    } catch (err) {
      const offline = err instanceof ApiError && err.offline;
      const message = err instanceof Error ? err.message : String(err);
      setTurns((t) => [
        ...t,
        {
          role: "error",
          text: offline
            ? `Could not reach the cognition gateway (${message}). Start the operator service or check the /api proxy.`
            : `The cognition gateway returned an error: ${message}`,
        },
      ]);
    } finally {
      setBusy(false);
      requestAnimationFrame(() =>
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }),
      );
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4 p-6">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Brain className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight">Operator Chat</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          The agentic cognition: repo-grounded where relevant, honest general knowledge
          otherwise, hard boundaries always enforced. Provenance is shown, never hidden.
        </p>
      </div>

      <LiveDataNotice />

      <div className="flex-1 overflow-y-auto rounded-lg border border-border/60" ref={scrollRef}>
        <div className="space-y-4 p-4">
          {turns.length === 0 && needsKey && (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <KeyRound className="h-8 w-8 text-muted-foreground" />
              <div className="space-y-1">
                <p className="text-sm font-medium">Connect a model to start chatting</p>
                <p className="max-w-sm text-sm text-muted-foreground">
                  Add an API key for any model and Aureon can reason for you. It takes a minute —
                  your key is stored encrypted and, when you're signed in, kept to your account alone.
                </p>
              </div>
              <Button asChild size="sm">
                <Link to="/cognition/providers">Add a model key</Link>
              </Button>
            </div>
          )}
          {turns.length === 0 && !needsKey && (
            <div className="space-y-2 py-8 text-center">
              <p className="text-sm text-muted-foreground">Ask anything — from the repo to the cosmos.</p>
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <Button key={s} size="sm" variant="outline" className="text-xs" onClick={() => ask(s)}>
                    {s}
                  </Button>
                ))}
              </div>
            </div>
          )}
          {turns.map((turn, i) => (
            <div key={i} className={turn.role === "user" ? "flex justify-end" : "flex justify-start"}>
              <Card
                className={
                  turn.role === "user"
                    ? "max-w-[85%] border-primary/30 bg-primary/10"
                    : turn.role === "error"
                      ? "max-w-[85%] border-destructive/40"
                      : "max-w-[85%] border-border/60"
                }
              >
                <CardContent className="space-y-2 p-3">
                  <p className="whitespace-pre-wrap text-sm">{turn.text}</p>
                  {turn.reply && (
                    <div className="flex flex-wrap items-center gap-1.5 border-t border-border/40 pt-2">
                      {turn.reply.blocked ? (
                        <Badge variant="outline" className="gap-1 border-destructive/40 text-destructive">
                          <ShieldAlert className="h-3 w-3" /> blocked · {turn.reply.conscience_verdict}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="gap-1 border-success/40 text-success">
                          <ShieldCheck className="h-3 w-3" /> {turn.reply.conscience_verdict || "APPROVED"}
                        </Badge>
                      )}
                      <Badge variant="outline" className="text-muted-foreground">
                        {turn.reply.envelope?.sources_statement ||
                          (turn.reply.grounded ? "repo-grounded" : "general knowledge")}
                      </Badge>
                      {turn.reply.envelope?.status && turn.reply.envelope.status !== "ok" && (
                        <Badge variant="outline" className="border-warning/40 text-warning">
                          {turn.reply.envelope.status.replace(/_/g, " ")}
                        </Badge>
                      )}
                      {turn.reply.envelope?.coherence?.lead_family && (
                        <Badge variant="outline" className="text-muted-foreground">
                          council lead: {turn.reply.envelope.coherence.lead_family.replace(/^safe_/, "").replace(/_/g, " ")}
                        </Badge>
                      )}
                      {turn.reply.envelope?.actualization &&
                        (turn.reply.envelope.actualization.parked_count ?? 0) > 0 && (
                          <Badge variant="outline" className="text-muted-foreground">
                            {turn.reply.envelope.actualization.realized_count ?? 0} realized ·{" "}
                            {turn.reply.envelope.actualization.parked_count} parked
                          </Badge>
                        )}
                      {turn.reply.envelope?.knowledge_reach &&
                        turn.reply.envelope.knowledge_reach.join(",") !== "general_knowledge" && (
                          <Badge variant="outline" className="text-muted-foreground">
                            reach: {turn.reply.envelope.knowledge_reach.join(" + ").replace(/_/g, " ")}
                          </Badge>
                        )}
                      {turn.reply.envelope?.acquisition?.triggered && (
                        <Badge variant="outline" className="text-muted-foreground">
                          acquired: {turn.reply.envelope.acquisition.outcome}
                        </Badge>
                      )}
                      {turn.reply.envelope?.coherence_gate?.aperture &&
                        turn.reply.envelope.coherence_gate.aperture !== "full" && (
                          <Badge variant="outline" className="border-warning/40 text-warning">
                            aperture: {turn.reply.envelope.coherence_gate.aperture}
                          </Badge>
                        )}
                      {typeof turn.reply.envelope?.heart?.alive?.symbolic_life_score === "number" && (
                        <Badge variant="outline" className="text-muted-foreground">
                          alive: {turn.reply.envelope.heart.alive.symbolic_life_score.toFixed(2)}
                        </Badge>
                      )}
                      {(turn.reply.envelope?.heart?.power?.withheld?.length ?? 0) > 0 && (
                        <Badge
                          variant="outline"
                          className="text-muted-foreground"
                          title={turn.reply.envelope?.heart?.power?.statement}
                        >
                          power held: {turn.reply.envelope?.heart?.power?.withheld?.length}
                        </Badge>
                      )}
                      {turn.reply.envelope?.bake?.refined && (
                        <Badge variant="outline" className="text-muted-foreground">
                          baked ×{turn.reply.envelope.bake.passes ?? 2}
                        </Badge>
                      )}
                      {turn.reply.envelope?.bake?.complete === false && (
                        <Badge variant="outline" className="border-warning/40 text-warning">
                          incomplete — honest seal
                        </Badge>
                      )}
                      {(turn.reply.tool_calls?.length ?? 0) > 0 && (
                        <Badge variant="outline" className="gap-1 text-muted-foreground">
                          <Wrench className="h-3 w-3" /> {turn.reply.tool_calls?.length} tool call
                          {(turn.reply.tool_calls?.length ?? 0) > 1 ? "s" : ""}
                        </Badge>
                      )}
                      {typeof turn.reply.elapsed_ms === "number" && (
                        <span className="text-[10px] text-muted-foreground">
                          {Math.round(turn.reply.elapsed_ms)} ms
                        </span>
                      )}
                    </div>
                  )}
                  {turn.reply?.grounding?.sources?.length ? (
                    <div className="space-y-0.5">
                      {turn.reply.grounding.sources.slice(0, 4).map((s, j) => (
                        <p key={j} className="truncate font-mono text-[10px] text-muted-foreground">
                           {s.path || s.title}
                          {s.score ? ` · ${s.score}` : ""}
                        </p>
                      ))}
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </div>
          ))}
          {busy && <p className="animate-pulse text-xs text-muted-foreground">Aureon is reasoning…</p>}
        </div>
      </div>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask(input);
            }
          }}
          placeholder="Ask the Aureon cognition… (Enter to send, Shift+Enter for newline)"
          className="min-h-[44px] resize-none"
          rows={1}
        />
        <Button type="submit" disabled={busy || !input.trim()} aria-label="Send">
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
