/**
 * LandingPage — the public front door (route "/").
 *
 * Backend-independent: renders fully without a gateway, so a first-time visitor or
 * investor sees a value proposition, the company behind it, verifiable trust signals,
 * and an evidence teaser — not offline telemetry. Enterprise tone; the mythopoeic HNC
 * voice is kept to a single accent line, not the headline.
 */

import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  BrainCircuit,
  ShieldCheck,
  FlaskConical,
  Radio,
  ArrowRight,
  BadgeCheck,
  ScrollText,
  Coins,
  Building2,
  Award,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { COMPANY, PRODUCT, RECOGNITION } from "../companyFacts";
import { HASH_REDIRECTS } from "../nav";

const PILLARS = [
  {
    icon: Activity,
    title: "Trading research",
    body: "Live market research and execution scaffolding — every action gated by explicit human approval. The platform never initiates trades autonomously.",
  },
  {
    icon: ShieldCheck,
    title: "Operator with a conscience",
    body: "An autonomous operator whose every consequential move passes a hard boundary check and a conscience veto — fail-safe by default, never silently passed.",
  },
  {
    icon: Radio,
    title: "Planetary / HNC research",
    body: "A falsifiable research fabric (the Harmonic Nexus Core) with pre-registered, reproducible predictions and honest data provenance throughout.",
  },
  {
    icon: BrainCircuit,
    title: "Self-building coding organism",
    body: "A coding system that proposes, tests, and hands over its own changes behind the same governance — auditable end to end.",
  },
];

const TRUST = [
  { icon: Building2, label: `Companies House ${COMPANY.companyNumber}`, detail: "Registered NI company" },
  { icon: Award, label: "Innovate NI · Silver", detail: `Recognised ${RECOGNITION.date}` },
  { icon: BadgeCheck, label: `${COMPANY.license} licensed`, detail: "Open source" },
  { icon: ShieldCheck, label: "Honest data provenance", detail: "No fabricated values" },
];

export default function LandingPage() {
  const navigate = useNavigate();

  // Preserve legacy #hash deep links that used to resolve at the old operator root
  // (e.g. /#trading → the console's trading tab). Runs once on first load.
  useEffect(() => {
    const hash = window.location.hash.split("/")[0];
    const target = HASH_REDIRECTS[hash];
    if (target) {
      const [path, keepHash] = target.split("#");
      navigate(path || "/console", { replace: true });
      window.location.hash = keepHash ? `#${keepHash}` : "";
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      {/* Hero — a visual anchor: gold-on-slate wash + faint nexus motif behind the copy */}
      <section className="relative overflow-hidden border-b border-border/60">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_120%_at_15%_-10%,hsl(var(--primary)/0.14),transparent_60%)]"
        />
        <svg
          aria-hidden
          viewBox="0 0 400 400"
          className="pointer-events-none absolute -right-16 -top-16 h-[28rem] w-[28rem] text-primary/20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
        >
          {[40, 90, 140, 190].map((r) => (
            <circle key={r} cx="200" cy="200" r={r} />
          ))}
          <path d="M200 10 L200 390 M10 200 L390 200" />
        </svg>

        <div className="relative mx-auto max-w-6xl px-4 py-20 sm:py-28">
          <Badge variant="outline" className="mb-5 gap-1.5 bg-background/60 text-xs">
            <BadgeCheck className="h-3.5 w-3.5 text-primary" />
            By {COMPANY.tradingName}
          </Badge>
          <h1 className="max-w-3xl text-4xl font-bold leading-[1.08] tracking-tight sm:text-6xl">
            The grounded AI operating layer for{" "}
            <span className="text-primary">high-control</span> work.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
            {PRODUCT.name} — {PRODUCT.summary}
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link to="/console">
                Open the console <ArrowRight className="ml-1.5 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/evidence">
                See the evidence <ArrowRight className="ml-1.5 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4">
        {/* Trust strip — credibility with chrome, not flat gray text */}
        <section className="grid grid-cols-2 gap-3 py-8 lg:grid-cols-4">
          {TRUST.map((t) => (
            <div key={t.label} className="flex items-start gap-3 rounded-lg border border-border bg-card p-4 shadow-sm">
              <t.icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div className="flex flex-col">
                <span className="text-sm font-medium text-foreground">{t.label}</span>
                <span className="text-xs text-muted-foreground">{t.detail}</span>
              </div>
            </div>
          ))}
        </section>

      {/* Pillars */}
      <section className="py-16">
        <h2 className="text-2xl font-semibold tracking-tight">One auditable system</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Four capabilities, one governance spine — a human approves what matters, and a conscience
          layer can always say no.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {PILLARS.map((p) => (
            <Card key={p.title}>
              <CardContent className="flex gap-4 p-5">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <p.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-medium">{p.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{p.body}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Evidence teaser */}
      <section className="py-14">
        <Card className="border-primary/20 bg-primary/[0.03]">
          <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-4">
              <FlaskConical className="h-6 w-6 shrink-0 text-primary" />
              <div>
                <h3 className="font-medium">Built to be falsified, not believed</h3>
                <p className="mt-1 max-w-xl text-sm text-muted-foreground">
                  The research thesis is stated as pre-registered, reproducible, falsifiable claims —
                  each with a source and a command to reproduce it. Due-diligence reviewers can audit
                  the evidence and the data-provenance model directly.
                </p>
              </div>
            </div>
            <Button asChild variant="outline" className="shrink-0">
              <Link to="/evidence">Evidence &amp; methodology</Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Commercial model — the real model, stated honestly (no invented tiers) */}
      <section className="py-14">
        <div className="flex items-center gap-2">
          <Coins className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-semibold tracking-tight">How Aureon is priced</h2>
        </div>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Aligned with the operator, not extractive. No seats, no lock-in, no invented tiers.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { title: "Free to run", body: "Open-source under the MIT licence and self-hostable. Clone it and run your own instance." },
            { title: "Performance-fee gas tank", body: "A prepaid wallet charged only as a fee on profit above your high-water mark. Usage metering is record-only." },
            { title: "Human-approved", body: "Sensitive actions — trading, payments — always require your explicit approval. The platform never initiates payments." },
            { title: "Optional support", body: "Support-the-project contributions keep the work going. They are voluntary, never a paywall." },
          ].map((m) => (
            <Card key={m.title}>
              <CardContent className="p-5">
                <h3 className="font-medium">{m.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{m.body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
        <p className="mt-4 text-xs text-muted-foreground">
          Full billing state and the prepaid wallet live in the console under{" "}
          <Link to="/platform/billing" className="underline hover:text-foreground">Billing &amp; Support</Link>.
        </p>
      </section>

        {/* Closing risk line — honest, understated, end of page (not in the hero) */}
        <section className="border-t border-border/60 py-8">
          <p className="flex items-start gap-2 text-xs text-muted-foreground">
            <ScrollText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <span>
              Aureon OS is research and operational software — not financial advice and not an offer
              of securities. Trading carries substantial risk to capital.{" "}
              <Link to="/legal#risk" className="underline hover:text-foreground">Read the risk disclosure.</Link>
            </span>
          </p>
        </section>
      </div>
    </div>
  );
}
