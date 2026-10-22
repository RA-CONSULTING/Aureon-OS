import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export type ChronicleSection = {
  id: string;
  title: string;
  badge?: string;
  metrics: Array<{ label: string; value: string }>;
  description: string;
};

export type ChronicleGovernance = {
  sections: ChronicleSection[];
  highlights: string[];
};

type ChronicleGovernanceTabProps = {
  governance: ChronicleGovernance;
};

const ChronicleGovernanceTab = ({ governance }: ChronicleGovernanceTabProps) => (
  <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(59,130,246,0.22)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),_transparent_60%)] opacity-80" />
    <CardHeader className="relative z-10 pb-4">
      <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Chronicle &amp; Data Governance</CardTitle>
      <p className="mt-2 max-w-2xl text-sm text-slate-300/85">
        Integrity seals, encryption vows, and archival vaults. Each panel glows with the authority of its directive.
      </p>
    </CardHeader>
    <CardContent className="relative z-10 space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {governance.sections.map((section) => (
          <div key={section.id} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]">
            <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
            <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
              <div className="pointer-events-none absolute inset-0 rounded-[calc(1rem-2px)] bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.12),_transparent_65%)] opacity-0 transition duration-500 group-hover:opacity-100" />
              <div className="relative z-10 flex items-start justify-between gap-3">
                <div className="text-sm font-semibold uppercase tracking-[0.22em] text-white">{section.title}</div>
                {section.badge ? (
                  <Badge className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]" variant="outline">
                    {section.badge}
                  </Badge>
                ) : null}
              </div>
              <p className="relative z-10 mt-2 text-xs text-slate-300/80">{section.description}</p>
              <dl className="relative z-10 mt-5 space-y-3 text-sm">
                {section.metrics.map((metric) => (
                  <div key={metric.label} className="flex items-baseline justify-between gap-3 rounded-xl border border-white/10 bg-white/5 p-3">
                    <dt className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">{metric.label}</dt>
                    <dd className="text-right text-sm font-semibold text-white">{metric.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        ))}
      </div>
      <div className="relative overflow-hidden rounded-2xl border border-dashed border-white/20 bg-white/5 p-5 text-sm text-slate-100">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-amber-500/25 via-transparent to-rose-500/25 opacity-80" />
        <div className="relative z-10 font-semibold uppercase tracking-[0.3em] text-white/85">Continuity Highlights</div>
        <ul className="relative z-10 mt-3 space-y-2 text-sm leading-relaxed text-slate-100/90">
          {governance.highlights.map((highlight) => (
            <li key={highlight} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[13px] tracking-[0.18em]">
              {highlight}
            </li>
          ))}
        </ul>
      </div>
    </CardContent>
  </Card>
);

export default ChronicleGovernanceTab;
