/**
 * Get Started — the guided first run.
 *
 * The one surface that orients a brand-new user: connect a model, confirm it
 * responds, then start reasoning. Every step reflects the live account state
 * (useSetupStatus), so the checklist is honest — it ticks itself as the user
 * actually completes each step, and never claims readiness the backend can't back.
 */

import { CheckCircle2, Circle, KeyRound, MessageSquare, Rocket, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSetupStatus } from "@/hooks/useSetupStatus";

type StepState = "done" | "current" | "todo";

function StepRow({
  index,
  icon: Icon,
  title,
  description,
  state,
  action,
}: {
  index: number;
  icon: typeof KeyRound;
  title: string;
  description: string;
  state: StepState;
  action?: { label: string; to: string };
}) {
  return (
    <div
      className={
        "flex gap-4 rounded-lg border p-4 transition-colors " +
        (state === "current" ? "border-primary/40 bg-primary/5" : "border-border/60")
      }
    >
      <div className="mt-0.5 shrink-0">
        {state === "done" ? (
          <CheckCircle2 className="h-6 w-6 text-emerald-500" />
        ) : (
          <span className="relative inline-flex h-6 w-6 items-center justify-center">
            <Circle className={"h-6 w-6 " + (state === "current" ? "text-primary" : "text-muted-foreground/40")} />
            <span className="absolute text-xs font-semibold tabular-nums">{index}</span>
          </span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <h3 className="font-medium">{title}</h3>
          {state === "done" && (
            <Badge variant="success" className="text-[10px]">
              done
            </Badge>
          )}
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      {action && state !== "done" && (
        <div className="shrink-0 self-center">
          <Button asChild size="sm" variant={state === "current" ? "default" : "outline"}>
            <Link to={action.to}>{action.label}</Link>
          </Button>
        </div>
      )}
    </div>
  );
}

export default function GetStartedPage() {
  const setup = useSetupStatus();

  const step1: StepState = setup.hasProvider ? "done" : "current";
  const step2: StepState = setup.liveProvider ? "done" : setup.hasProvider ? "current" : "todo";
  const step3: StepState = setup.hasProvider ? "current" : "todo";
  const ready = setup.hasProvider;

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Rocket className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Get Started</h1>
          <p className="text-sm text-muted-foreground">
            Three steps to your first grounded conversation with Aureon. The checklist ticks itself as
            you go — nothing here is faked.
          </p>
        </div>
      </div>

      {setup.loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {!setup.loading && setup.offline && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">The Aureon backend isn't reachable yet</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            This page needs the operator gateway running. If you're on the hosted app, give it a moment
            and refresh; if you're running locally, start the operator service, then reload.
          </CardContent>
        </Card>
      )}

      {!setup.loading && !setup.offline && (
        <>
          {ready && (
            <Card className="border-emerald-500/30 bg-emerald-500/5">
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-emerald-500" />
                  <span className="text-sm font-medium">
                    You're set up — {setup.providerCount} model
                    {setup.providerCount === 1 ? "" : "s"} connected. Start a conversation.
                  </span>
                </div>
                <Button asChild size="sm">
                  <Link to="/cognition/operator">Open Operator Chat</Link>
                </Button>
              </CardContent>
            </Card>
          )}

          <div className="space-y-3">
            <StepRow
              index={1}
              icon={KeyRound}
              title="Connect a model"
              description="Paste an API key for any model (OpenAI, Anthropic, Gemini, Grok, or a local one) on the Providers page. Keys are encrypted at rest, masked on read, and — when you're signed in — scoped to your account alone."
              state={step1}
              action={{ label: setup.hasProvider ? "Manage keys" : "Add a key", to: "/cognition/providers" }}
            />
            <StepRow
              index={2}
              icon={ShieldCheck}
              title="Test the connection"
              description="Run a real round-trip from the Providers page to confirm your key works. An honest verdict — reachable or not — comes straight back; nothing is assumed."
              state={step2}
              action={{ label: "Test on Providers", to: "/cognition/providers" }}
            />
            <StepRow
              index={3}
              icon={MessageSquare}
              title="Start reasoning"
              description="Open Operator Chat and ask anything — from the repository to the cosmos. Answers show their provenance: repo grounding, tool calls, and the conscience verdict, never hidden."
              state={step3}
              action={{ label: "Open Operator Chat", to: "/cognition/operator" }}
            />
          </div>
        </>
      )}
    </div>
  );
}
