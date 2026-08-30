/**
 * Systems & Coverage — the live repo-wide coverage of the SaaS.
 *
 * Reads GET /api/coverage and renders the honest reconciliation of the real
 * aureon/ package tree against the SaaS taxonomy + catalog: how many packages
 * are covered, any uncovered (on-disk-but-unmapped) or phantom (mapped-but-absent)
 * domains, and — for every covered domain — its real operational health rollup
 * (modules · dashboards · wired fraction · LOC · capabilities), all derived from
 * the filesystem scan. Nothing is fabricated; a dormant domain shows no rollup.
 */

import { useEffect, useMemo, useState } from "react";
import { Boxes, CircleCheck, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";

interface DomainHealth {
  system_count: number;
  dashboards: number;
  queen_integrated: number;
  bus_wired: number;
  wired_count: number;
  wired_fraction: number;
  total_loc: number;
  capabilities: string[];
}

interface CoverageDomain {
  domain: string;
  product_domain: string;
  has_adapter: boolean;
  health: DomainHealth | null;
}

interface BenchmarkCoverage {
  status: string;
  benchmarks: number;
  module_pin_count: number;
  total_modules: number;
  covered_domains: string[];
  uncovered_domains: string[];
  domain_coverage_fraction: number | null;
  ratchet?: { ok: boolean; regressions: string[] };
}

interface CoveragePayload {
  fs_package_count: number;
  taxonomy_count: number;
  covered: string[];
  uncovered: string[];
  phantom: string[];
  coverage_fraction: number;
  all_covered: boolean;
  adapter_deep_count: number;
  surfaced_with_systems: number;
  domains: CoverageDomain[];
  benchmark_coverage?: BenchmarkCoverage;
  note?: string;
  truth_status?: string;
}

function StatTile({ label, value, tone }: { label: string; value: string | number; tone?: "good" | "warn" }) {
  return (
    <div className="rounded-lg border bg-card/50 px-4 py-3">
      <div
        className={
          "text-2xl font-semibold tabular-nums " +
          (tone === "warn" ? "text-amber-500" : tone === "good" ? "text-emerald-500" : "text-foreground")
        }
      >
        {value}
      </div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function DomainRow({ d }: { d: CoverageDomain }) {
  const h = d.health;
  const wiredPct = h ? Math.round(h.wired_fraction * 100) : 0;
  return (
    <tr className="border-t text-sm hover:bg-muted/40">
      <td className="py-2 pl-3 pr-2 font-mono">{d.domain}</td>
      <td className="px-2 text-muted-foreground">{d.product_domain}</td>
      <td className="px-2">
        <Badge variant={d.has_adapter ? "success" : "outline"} className="text-[10px]">
          {d.has_adapter ? "deep" : "probe"}
        </Badge>
      </td>
      <td className="px-2 text-right tabular-nums">{h ? h.system_count : "—"}</td>
      <td className="px-2 text-right tabular-nums">{h ? h.dashboards : "—"}</td>
      <td className="px-2 text-right tabular-nums">
        {h ? (
          <span className="inline-flex items-center gap-2">
            <span className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-muted sm:inline-block">
              <span className="block h-full rounded-full bg-primary" style={{ width: `${wiredPct}%` }} />
            </span>
            {wiredPct}%
          </span>
        ) : (
          "—"
        )}
      </td>
      <td className="px-2 text-right tabular-nums">{h ? h.total_loc.toLocaleString() : "—"}</td>
      <td className="hidden px-3 text-right text-xs text-muted-foreground md:table-cell">
        {h ? h.capabilities.length : 0}
      </td>
    </tr>
  );
}

export default function SystemsCoveragePage() {
  const [data, setData] = useState<CoveragePayload | null | undefined>(undefined);

  useEffect(() => {
    fetch("/api/coverage")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => setData(null));
  }, []);

  const domains = useMemo(
    () => (data ? [...data.domains].sort((a, b) => (b.health?.system_count ?? 0) - (a.health?.system_count ?? 0)) : []),
    [data],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Boxes className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Systems & Coverage</h1>
          <p className="text-sm text-muted-foreground">
            Live repo-wide coverage — every <span className="font-mono">aureon/</span> package reconciled
            against the SaaS taxonomy, each domain with its real operational health. Derived from the
            filesystem scan; nothing fabricated.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {data === undefined && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      )}

      {data === null && (
        <Card>
          <CardHeader>
            <CardTitle>Gateway offline</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Start the operator to load the live <span className="font-mono">/api/coverage</span> surface.
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  {data.all_covered ? (
                    <CircleCheck className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <TriangleAlert className="h-4 w-4 text-amber-500" />
                  )}
                  {data.covered.length} of {data.fs_package_count} packages covered
                </CardTitle>
                <Badge variant={data.all_covered ? "success" : "secondary"}>
                  {Math.round(data.coverage_fraction * 100)}% covered
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                <StatTile label="packages covered" value={`${data.covered.length}/${data.fs_package_count}`} tone="good" />
                <StatTile label="uncovered" value={data.uncovered.length} tone={data.uncovered.length ? "warn" : undefined} />
                <StatTile label="phantom (stale)" value={data.phantom.length} tone={data.phantom.length ? "warn" : undefined} />
                <StatTile label="deep adapters" value={data.adapter_deep_count} />
                <StatTile label="domains with systems" value={data.surfaced_with_systems} />
              </div>
              {(data.uncovered.length > 0 || data.phantom.length > 0) && (
                <div className="mt-3 space-y-1 text-xs text-amber-600">
                  {data.uncovered.length > 0 && (
                    <p>uncovered (on disk, unmapped): {data.uncovered.map((d) => `\`${d}\``).join(", ")}</p>
                  )}
                  {data.phantom.length > 0 && (
                    <p>phantom (mapped, absent): {data.phantom.map((d) => `\`${d}\``).join(", ")}</p>
                  )}
                </div>
              )}
              {data.note && <p className="mt-3 text-[11px] text-muted-foreground">{data.note}</p>}
            </CardContent>
          </Card>

          {data.benchmark_coverage && data.benchmark_coverage.status === "measured" && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle className="text-base">Benchmark coverage — the march to 100%</CardTitle>
                  <Badge variant={data.benchmark_coverage.ratchet?.ok ? "success" : "secondary"}>
                    ratchet {data.benchmark_coverage.ratchet?.ok ? "holding" : "regressed"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatTile label="Tier-A benchmarks" value={data.benchmark_coverage.benchmarks} tone="good" />
                  <StatTile
                    label="modules pinned"
                    value={`${data.benchmark_coverage.module_pin_count}/${data.benchmark_coverage.total_modules}`}
                  />
                  <StatTile
                    label="domains pinned"
                    value={`${data.benchmark_coverage.covered_domains.length}/${
                      data.benchmark_coverage.covered_domains.length +
                      data.benchmark_coverage.uncovered_domains.length
                    }`}
                  />
                  <StatTile
                    label="roadmap (unpinned)"
                    value={data.benchmark_coverage.uncovered_domains.length}
                    tone={data.benchmark_coverage.uncovered_domains.length ? "warn" : "good"}
                  />
                </div>
                {data.benchmark_coverage.uncovered_domains.length > 0 && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    roadmap: {data.benchmark_coverage.uncovered_domains.join(" · ")}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Per-domain operational health</CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] border-collapse">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                      <th className="py-2 pl-3 pr-2 font-medium">domain</th>
                      <th className="px-2 font-medium">product</th>
                      <th className="px-2 font-medium">adapter</th>
                      <th className="px-2 text-right font-medium">systems</th>
                      <th className="px-2 text-right font-medium">dashboards</th>
                      <th className="px-2 text-right font-medium">wired</th>
                      <th className="px-2 text-right font-medium">LOC</th>
                      <th className="hidden px-3 text-right font-medium md:table-cell">caps</th>
                    </tr>
                  </thead>
                  <tbody>
                    {domains.map((d) => (
                      <DomainRow key={d.domain} d={d} />
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
