/**
 * Company — the organization behind Aureon OS.
 *
 * Reads GET /api/org and renders R&A Consulting and Brokerage Services Ltd
 * (trading as Aureon Zorza Technologies): the registered company facts, the
 * Innovate NI Silver recognition, community support, and contact — all
 * verifiable public data transcribed from COMPANY.md, carried with an honest
 * data-provenance badge. Nothing is fabricated; with no backend it shows the
 * honest offline state.
 */

import { useEffect, useState } from "react";
import { Award, Building2, ExternalLink, HeartHandshake, ScrollText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";
import { type TruthStatus, TRUTH_STATUS_STYLE } from "../truthStatus";
import { buildStaticCompanyProfile } from "../companyFacts";


interface OrgProfile {
  identity: Record<string, string>;
  identity_note: string;
  recognition: Record<string, string>;
  community: { summary: string; partners: string[] };
  product: Record<string, string>;
  contact: Record<string, string>;
  disclaimer: string;
  source?: string;
  truth_status: TruthStatus;
}

const STATUS_STYLE: Record<TruthStatus, { cls: string; label: string }> = {
  live: { cls: TRUTH_STATUS_STYLE.live, label: "live" },
  real_derived: { cls: TRUTH_STATUS_STYLE.real_derived, label: "real · derived" },
  cached_real: { cls: TRUTH_STATUS_STYLE.cached_real, label: "cached real" },
  no_data: { cls: TRUTH_STATUS_STYLE.no_data, label: "no data" },
  test_fixture: { cls: TRUTH_STATUS_STYLE.test_fixture, label: "test fixture" },
};

function StatusBadge({ status }: { status: TruthStatus }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.no_data;
  return <Badge variant="outline" className={`text-[10px] ${s.cls}`}>{s.label}</Badge>;
}

/** Turn snake_case keys into a human label ("company_number" → "Company number"). */
function humanize(key: string): string {
  const s = key.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const IDENTITY_ORDER = [
  "registered_name", "company_number", "registrar", "status",
  "registered_office", "director", "trading_name", "research_identity", "website",
];

export default function CompanyPage() {
  const [data, setData] = useState<OrgProfile | null | undefined>(undefined);

  useEffect(() => {
    // Prefer the live gateway; fall back to the committed static facts so the company
    // story is never blank — the facts are identical (both real_derived from COMPANY.md).
    fetch("/api/org")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => setData(buildStaticCompanyProfile() as OrgProfile));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Building2 className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Company</h1>
          <p className="text-sm text-muted-foreground">
            The organization behind Aureon OS — verifiable public facts, not marketing.
          </p>
        </div>
        {data && <StatusBadge status={data.truth_status} />}
      </div>

      <LiveDataNotice />

      {data === undefined && (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 w-full" />)}</div>
      )}
      {data === null && (
        <Card><CardHeader><CardTitle>Gateway offline</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Start the operator gateway for the live company profile. The facts are also in
            <span className="font-mono"> COMPANY.md</span> at the repository root.
          </CardContent></Card>
      )}

      {data && (
        <>
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-primary" />
                <CardTitle className="text-base">Registered company</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
                {IDENTITY_ORDER.filter((k) => data.identity[k]).map((k) => (
                  <div key={k} className="flex flex-col">
                    <dt className="text-xs uppercase tracking-wide text-muted-foreground">{humanize(k)}</dt>
                    <dd className="text-sm">
                      {k === "website" ? (
                        <a className="inline-flex items-center gap-1 text-primary hover:underline"
                           href={data.identity[k]} target="_blank" rel="noreferrer">
                          {data.identity[k].replace(/^https?:\/\//, "")}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : k === "company_number" ? (
                        <span className="font-mono">{data.identity[k]}</span>
                      ) : (
                        data.identity[k]
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="text-xs text-muted-foreground border-t border-border/60 pt-3">{data.identity_note}</p>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Award className="h-4 w-4 text-warning" />
                  <CardTitle className="text-base">Recognition</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="font-medium">{data.recognition.award}</p>
                <p className="text-muted-foreground">{data.recognition.issuer}</p>
                <p className="text-xs text-muted-foreground">
                  {data.recognition.signatory} · {data.recognition.date}
                </p>
                <p className="text-xs text-muted-foreground">{data.recognition.detail}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <HeartHandshake className="h-4 w-4 text-primary" />
                  <CardTitle className="text-base">Community</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="text-muted-foreground">{data.community.summary}</p>
                <div className="flex flex-wrap gap-1.5">
                  {data.community.partners.map((p) => (
                    <Badge key={p} variant="secondary" className="text-[10px]">{p}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{data.product.name} · {data.product.powered_by}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="text-muted-foreground">{data.product.summary}</p>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                {data.contact.website && (
                  <a className="inline-flex items-center gap-1 text-primary hover:underline"
                     href={data.contact.website} target="_blank" rel="noreferrer">
                    {data.contact.website.replace(/^https?:\/\//, "")}<ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {data.contact.repository && (
                  <a className="inline-flex items-center gap-1 text-primary hover:underline"
                     href={data.contact.repository} target="_blank" rel="noreferrer">
                    repository<ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {data.contact.license && <span className="text-muted-foreground">License: {data.contact.license}</span>}
                {data.contact.copyright && <span className="text-muted-foreground">{data.contact.copyright}</span>}
              </div>
            </CardContent>
          </Card>

          <p className="flex items-start gap-2 text-[11px] text-muted-foreground">
            <ScrollText className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {data.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}
