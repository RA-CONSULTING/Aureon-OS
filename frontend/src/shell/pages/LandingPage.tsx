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
  { label: `Companies House ${COMPANY.companyNumber}`, detail: "Registered NI company" },
  { label: "Innovate NI · Silver", detail: RECOGNITION.date },
  { label: `${COMPANY.license} licensed`, detail: "Open source" },
  { label: "Honest data provenance", detail: "No fabricated values" },
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
    <div className="mx-auto max-w-6xl px-4">
      {/* Hero */}
      <section className="py-16 sm:py-24">
        <Badge variant="outline" className="mb-5 gap-1.5 text-xs">
          <BadgeCheck className="h-3.5 w-3.5 text-primary" />
          By {COMPANY.registeredName}
        </Badge>
        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
          {PRODUCT.name} — {PRODUCT.tagline}
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
          {PRODUCT.summary}
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Button asChild size="lg">
            <Link to="/console">
              Open the console <ArrowRight className="ml-1.5 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/evidence">See the evidence</Link>
          </Button>
        </div>
        <p className="mt-6 max-w-2xl text-xs text-muted-foreground">
          Aureon OS is research and operational software — <strong className="text-foreground">not
          financial advice</strong> and not an offer of securities. Trading carries substantial risk
          to capital.{" "}
          <Link to="/legal#risk" className="underline hover:text-foreground">Read the risk disclosure.</Link>
        </p>
      </section>

      {/* Trust strip */}
      <section className="grid grid-cols-2 gap-3 border-y border-border/60 py-6 lg:grid-cols-4">
        {TRUST.map((t) => (
          <div key={t.label} className="flex flex-col">
            <span className="text-sm font-medium text-foreground">{t.label}</span>
            <span className="text-xs text-muted-foreground">{t.detail}</span>
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
      <section className="py-8">
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
      <section className="py-8">
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

      {/* Voice accent — a single line, not the headline */}
      <section className="border-t border-border/60 py-10">
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <ScrollText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <span>
            The name is deliberate: a harmonic nexus — the same φ² coherence the research traces from
            ancient structures to market dynamics. The mysticism is framing; the claims underneath are
            measurable and pre-registered.
          </span>
        </p>
      </section>
    </div>
  );
}
