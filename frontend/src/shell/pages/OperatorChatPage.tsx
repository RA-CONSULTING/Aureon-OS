/**
 * Operator Chat — talk to the grounded Aureon cognition.
 *
 * POSTs to the gateway's /api/cognition/reason (through the nginx /api proxy)
 * and renders the full provenance honestly: repo grounding sources, tool calls,
 * the conscience verdict, and blocks. No backend → a clear offline notice.
 */

import { useRef, useState } from "react";
import { Brain, Send, ShieldAlert, ShieldCheck, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { LiveDataNotice } from "../Page";

interface GroundingSource {
  title?: string;
  path?: string;
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

  const ask = async (prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed || busy) return;
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { role: "user", text: trimmed }]);
    try {
      const r = await fetch("/api/cognition/reason", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: trimmed }),
      });
      if (!r.ok) throw new Error(`gateway returned ${r.status}`);
      const reply = (await r.json()) as CognitionReply;
      setTurns((t) => [...t, { role: "aureon", text: reply.text || "(empty answer)", reply }]);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setTurns((t) => [
        ...t,
        {
          role: "error",
          text: `Could not reach the cognition gateway (${message}). Start the operator service (:8790) or check the /api proxy.`,
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
          {turns.length === 0 && (
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
                        {turn.reply.grounded ? "repo-grounded" : "general knowledge"}
                      </Badge>
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
