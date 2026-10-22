import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const supportTracks = [
  {
    title: 'Guardian Concierge',
    description: 'Direct line to Aureon strategists for escalation, optimization, and investor narratives.',
    actions: ['Book alignment review', 'Request investor collateral', 'Escalate anomaly response'],
  },
  {
    title: 'Training Pathways',
    description: 'Live and on-demand curriculum covering execution, compliance, and storytelling mastery.',
    actions: ['Schedule live cohort', 'Download certification map', 'Access tutorial archive'],
  },
  {
    title: 'Platform Status',
    description: 'Real-time updates on lattice health, release cadence, and maintenance windows.',
    actions: ['View status dashboard', 'Subscribe to alerts', 'Review release notes'],
  },
];

const SupportPage = () => (
  <section className="space-y-12">
    <header className="space-y-4">
      <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
        Support Nexus
      </Badge>
      <h1 className="text-3xl font-semibold tracking-[0.28em] text-white">Always-on guidance for every guardian</h1>
      <p className="max-w-3xl text-sm leading-relaxed text-slate-200/80">
        Whether you are launching a new desk, preparing investor updates, or running emergency stabilization, the QGITA support mesh keeps your team protected.
      </p>
    </header>
    <div className="grid gap-6 lg:grid-cols-3">
      {supportTracks.map((track) => (
        <Card key={track.title} className="border-white/10 bg-white/5">
          <CardHeader>
            <CardTitle className="text-base font-semibold tracking-[0.22em] text-white/80">{track.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm leading-relaxed text-slate-200/80">
            <p>{track.description}</p>
            <div className="space-y-2 text-xs uppercase tracking-[0.3em] text-white/60">
              {track.actions.map((action) => (
                <Button key={action} variant="ghost" className="w-full border border-white/20 bg-transparent text-white hover:bg-white/10">
                  {action}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  </section>
);

export default SupportPage;
