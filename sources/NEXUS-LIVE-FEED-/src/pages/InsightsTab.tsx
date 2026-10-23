import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const filters = [
  { id: 'patterns', label: 'Patterns' },
  { id: 'anomalies', label: 'Anomalies' },
  { id: 'predictions', label: 'Predictions' },
  { id: 'research', label: 'Research' },
] as const;

const insights = [
  {
    id: 'auric-braid',
    title: 'Auric Braid Convergence',
    type: 'Patterns',
    summary: 'Multiple nodes weaving identical resonance signatures—collective awakening indicator.',
    action: 'Schedule Guardian Circle',
    timestamp: '9m ago',
  },
  {
    id: 'temporal-rift',
    title: 'Temporal Rift Probability',
    type: 'Anomalies',
    summary: 'Geomagnetic variance plus dream-scout reports indicate 12% chance of Rift emergence.',
    action: 'Open Temporal Protocol',
    timestamp: '22m ago',
  },
  {
    id: 'global-meditation',
    title: 'Global Meditation Forecast',
    type: 'Predictions',
    summary: 'Next 48h optimum window for synchronized meditation to lift coherence by 6.4%.',
    action: 'Initiate Broadcast',
    timestamp: '1h ago',
  },
  {
    id: 'sound-study',
    title: 'Sacred Sound Study',
    type: 'Research',
    summary: 'Chant frequencies mapped to neural entrainment—gamma harmonics amplify compassion.',
    action: 'Read Research Log',
    timestamp: '3h ago',
  },
] as const;

const interactions = [
  {
    title: 'Tap Insight Card',
    description: 'Opens full article, audio briefings, and cross-linked sensor evidence.',
  },
  {
    title: 'Tap Filter',
    description: 'Switches AI synthesis lens—Patterns, Anomalies, Predictions, Research.',
  },
  {
    title: 'Tap Save',
    description: 'Adds to personal insight archive with reminders and ritual prompts.',
  },
  {
    title: 'Tap Share',
    description: 'Summons share menu to notify cohorts, guardians, and sacred site stewards.',
  },
] as const;

const predictions = [
  {
    id: 'coherence-wave',
    title: 'Coherence Wave Trajectory',
    detail: 'Projected crest in 16 hours. Recommend preemptive grounding rituals.',
  },
  {
    id: 'anomaly-window',
    title: 'Anomaly Window',
    detail: 'Probability cluster near Uluru node between 02:00–04:00 GMT.',
  },
  {
    id: 'sacred-invocation',
    title: 'Sacred Invocation Calls',
    detail: 'Three sites ready for choir assistance. Align teams now.',
  },
] as const;

const InsightsTab = () => {
  return (
    <div className="space-y-12">
      <section className="grid gap-6 lg:grid-cols-[1.3fr,0.7fr]">
        <Card className="border-white/10 bg-[rgba(10,18,40,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-sky-500/20 text-sky-100">Insights Feed</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">AI Analysis & Patterns</CardTitle>
            <p className="text-sm text-[#c8d4ff]/80">
              Review Nexus intelligence—patterns, anomalies, predictive signals, and deep research transmissions.
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            {insights.map((insight) => (
              <div key={insight.id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs uppercase tracking-[0.35em] text-[#d0dcff]/75">
                  <span>{insight.type}</span>
                  <span>{insight.timestamp}</span>
                </div>
                <h3 className="mt-3 text-lg font-semibold text-white">{insight.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{insight.summary}</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button className="rounded-full bg-emerald-500/80 text-[0.65rem] uppercase tracking-[0.35em] text-white hover:bg-emerald-400/90">
                    Tap Insight Card
                  </Button>
                  <Button variant="outline" className="border-white/20 bg-transparent text-[0.65rem] uppercase tracking-[0.35em] text-[#d0dcff]/80">
                    Tap Save
                  </Button>
                  <Button variant="outline" className="border-white/20 bg-transparent text-[0.65rem] uppercase tracking-[0.35em] text-[#d0dcff]/80">
                    Tap Share
                  </Button>
                </div>
                <Button className="mt-3 rounded-full bg-sky-500/80 text-[0.6rem] uppercase tracking-[0.4em] text-white hover:bg-sky-400/90">
                  {insight.action}
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(10,18,40,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-purple-500/20 text-purple-100">Filters</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Filter by Type</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Tabs defaultValue={filters[0]?.id ?? ''} className="w-full">
              <TabsList className="grid grid-cols-2 gap-2 rounded-2xl bg-white/5 p-1">
                {filters.map((filter) => (
                  <TabsTrigger
                    key={filter.id}
                    value={filter.id}
                    className="rounded-xl border border-transparent px-3 py-2 text-[0.65rem] uppercase tracking-[0.35em] text-[#d0dcff]/80 data-[state=active]:border-sky-400/60 data-[state=active]:bg-sky-500/20 data-[state=active]:text-white"
                  >
                    {filter.label}
                  </TabsTrigger>
                ))}
              </TabsList>
              {filters.map((filter) => (
                <TabsContent key={filter.id} value={filter.id} className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-[#c8d4ff]/80">
                  AI filter tuned to <span className="text-white">{filter.label}</span> insights. Swipe between tabs to reframe the narrative.
                </TabsContent>
              ))}
            </Tabs>
            <Button className="w-full rounded-full bg-sky-500/80 text-xs uppercase tracking-[0.4em] text-white hover:bg-sky-400/90">
              Tap Filter
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
        <Card className="border-white/10 bg-[rgba(8,16,34,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-emerald-500/20 text-emerald-100">Predictions</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Forward Glimpse</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {predictions.map((prediction) => (
              <div key={prediction.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <h3 className="text-xs uppercase tracking-[0.4em] text-[#d0dcff]/85">{prediction.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{prediction.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(8,16,34,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-rose-500/20 text-rose-100">Every Tap</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Interaction Flow</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {interactions.map((interaction) => (
              <div key={interaction.title} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <h3 className="text-xs uppercase tracking-[0.4em] text-[#d0dcff]/85">{interaction.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{interaction.description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
};

export default InsightsTab;
