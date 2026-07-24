/**
 * EvidencePage — public /evidence.
 *
 * Surfaces the falsifiable-claims thesis for a due-diligence reviewer: pre-registered
 * predictions, a 5-minute reproduce-it-yourself test, links to the methodology /
 * falsification protocol / verification pack, and an in-app legend for the TruthStatus
 * data-provenance system used across the console. Backend-independent; every claim
 * links back to a source in the repository.
 */

import { FlaskConical, GitBranch, ExternalLink, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { COMPANY } from "../companyFacts";
import { TRUTH_STATUS_STYLE } from "../truthStatus";

const REPO = COMPANY.repository;
const doc = (path: string) => `${REPO}/blob/main/${path}`;

const PREDICTIONS = [
  { id: "P1", claim: "4I eccentricity within 10% of φ⁻ⁿ for some integer n", falsify: "On 4I discovery (Vera Rubin Observatory)" },
  { id: "P2", claim: "4I arrival time N × φ² years from the Wow! signal (±2.5%)", falsify: "4I discovery date" },
  { id: "P3", claim: "4I velocity within 10% of φ³ × 26.33 km/s ≈ 115 km/s", falsify: "4I orbit solution" },
  { id: "P4", claim: "GitHub node activation surges within 24–48h of a stress event", falsify: "Next geopolitical stress event" },
  { id: "P5", claim: "Gold fails as a safe-haven in the next major crisis", falsify: "Next major global crisis" },
];

const TRUTH_LEGEND = [
  { key: "live", label: "live", meaning: "Streaming from a running backend right now." },
  { key: "real_derived", label: "real · derived", meaning: "Computed from real committed data or documents." },
  { key: "cached_real", label: "cached real", meaning: "Real data from a recent cache, not this instant." },
  { key: "no_data", label: "no data", meaning: "No source connected — shown honestly as empty, never guessed." },
  { key: "test_fixture", label: "test fixture", meaning: "Sample/fixture data, explicitly labelled as such." },
] as const;

const LINKS = [
  { label: "Claims & Evidence (all claims → source → reproduce command)", path: "docs/CLAIMS_AND_EVIDENCE.md" },
  { label: "HNC Falsification Protocol", path: "docs/HNC_FALSIFICATION_PROTOCOL.md" },
  { label: "HNC Unified White Paper", path: "docs/HNC_UNIFIED_WHITE_PAPER.md" },
  { label: "Research Hub (methodology §3)", path: "docs/research/AUREON_WHITE_PAPER_RESEARCH_HUB.md" },
];

export default function EvidencePage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <header>
        <h1 className="flex items-center gap-2 text-3xl font-semibold tracking-tight">
          <FlaskConical className="h-7 w-7 text-primary" />
          Evidence &amp; Methodology
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Aureon is built to be falsified, not believed. The research thesis is stated as
          pre-registered, reproducible claims — each with a source and a way to check it — and every
          data surface in the console is labelled with where its numbers came from. This page is for
          reviewers who want to audit rather than take our word.
        </p>
      </header>

      {/* Pre-registered predictions */}
      <section className="mt-10">
        <h2 className="text-xl font-semibold tracking-tight">Pre-registered, falsifiable predictions</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Commitments made ahead of confirming data, so anyone can attempt to falsify the framework.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="py-2 pr-3 font-medium">#</th>
                <th className="py-2 pr-3 font-medium">Prediction</th>
                <th className="py-2 font-medium">How to falsify</th>
              </tr>
            </thead>
            <tbody>
              {PREDICTIONS.map((p) => (
                <tr key={p.id} className="border-b border-border/50 align-top">
                  <td className="py-2 pr-3 font-mono text-primary">{p.id}</td>
                  <td className="py-2 pr-3">{p.claim}</td>
                  <td className="py-2 text-muted-foreground">{p.falsify}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 5-minute skeptic test */}
      <section className="mt-10">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <GitBranch className="h-4 w-4 text-primary" />
              5-minute skeptic test
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              To check the single most important claim (C1: r = 0.85 oil ↔ node-activation
              correlation) yourself:
            </p>
            <ol className="list-decimal space-y-1 pl-5">
              <li>Clone the repository and read the methodology (Research Hub §3).</li>
              <li>Inspect the committed traffic evidence under <span className="font-mono text-xs">docs/research/traffic/</span>.</li>
              <li>Pull the comparable financial series (e.g. Brent, <span className="font-mono text-xs">BZ=F</span>) for the window.</li>
              <li>Compute the Pearson r yourself against the tracked GitHub activation window.</li>
            </ol>
            <p>
              Full step-by-step replication (traceability matrix, acceptance criteria, replication
              guidelines) ships in the <span className="font-mono text-xs">VERIFICATION AND VALIDATION/</span> pack.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Provenance legend */}
      <section className="mt-10">
        <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
          <ShieldCheck className="h-5 w-5 text-primary" />
          How to read the data labels
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Every metric in the console carries a provenance badge. No value is ever fabricated to look
          live — a dormant source reports “no data”, never a guess.
        </p>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {TRUTH_LEGEND.map((t) => (
            <div key={t.key} className="flex items-start gap-3 rounded-md border border-border/60 p-3">
              <Badge variant="outline" className={`shrink-0 text-[10px] ${TRUTH_STATUS_STYLE[t.key]}`}>
                {t.label}
              </Badge>
              <span className="text-xs text-muted-foreground">{t.meaning}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Source links */}
      <section className="mt-10 border-t border-border/60 pt-8">
        <h2 className="text-xl font-semibold tracking-tight">Read the sources</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {LINKS.map((l) => (
            <li key={l.path}>
              <a
                href={doc(l.path)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-primary hover:underline"
              >
                {l.label}
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
