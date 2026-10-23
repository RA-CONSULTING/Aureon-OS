import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const resourceCollections = [
  {
    title: 'Investor Narratives',
    description: 'Story-driven decks translating Aureon telemetry into executive conviction.',
    assets: ['Flagship pitch deck', 'Due diligence checklist', 'Quarterly performance storyboard'],
  },
  {
    title: 'Technical Deep Dives',
    description: 'Whitepapers and architecture briefs unpacking the QGITA lattice.',
    assets: ['Signal calibration whitepaper', 'Compliance mapping matrix', 'Guardian agent overview'],
  },
  {
    title: 'Activation Playbooks',
    description: 'Step-by-step guides for onboarding desks, investors, and strategic partners.',
    assets: ['21-day launch plan', 'Investor FAQ script', 'Guardian escalation protocol'],
  },
];

const ResourcesPage = () => (
  <section className="space-y-12">
    <header className="space-y-4">
      <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
        Resource Vault
      </Badge>
      <h1 className="text-3xl font-semibold tracking-[0.28em] text-white">Equip your team and investors instantly</h1>
      <p className="max-w-3xl text-sm leading-relaxed text-slate-200/80">
        Downloadable assets engineered to accelerate diligence, articulate the Aureon advantage, and keep every stakeholder aligned with your growth narrative.
      </p>
    </header>

    <div className="grid gap-6 lg:grid-cols-3">
      {resourceCollections.map((collection) => (
        <Card key={collection.title} className="border-white/10 bg-white/5">
          <CardHeader>
            <CardTitle className="text-base font-semibold tracking-[0.22em] text-white/80">{collection.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm leading-relaxed text-slate-200/80">
            <p>{collection.description}</p>
            <ul className="space-y-2 text-xs uppercase tracking-[0.3em] text-white/60">
              {collection.assets.map((asset) => (
                <li key={asset} className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2">
                  {asset}
                </li>
              ))}
            </ul>
            <Button variant="ghost" className="w-full border border-white/20 bg-transparent text-white hover:bg-white/10">
              Access Files
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  </section>
);

export default ResourcesPage;
