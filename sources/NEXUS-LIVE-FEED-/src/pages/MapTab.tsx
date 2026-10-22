import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const sensorNodes = [
  {
    id: 'cusco-array',
    name: 'Cusco Witness Array',
    status: 'Stable',
    reading: 'Coherence 0.86',
    detail: 'Triangulating Andean ley pulse with deep-earth resonance.',
  },
  {
    id: 'lagrange-relay',
    name: 'Lagrange L1 Orbital Relay',
    status: 'Watch',
    reading: 'Solar Wind 612 km/s',
    detail: 'Monitoring auric shimmer across magnetosphere.',
  },
  {
    id: 'giza-anchor',
    name: 'Giza Apex Anchor',
    status: 'Stable',
    reading: 'Phase Lock 99.2%',
    detail: 'Pyramid lattice distributing coherence to African grid.',
  },
  {
    id: 'uluru-node',
    name: 'Uluru Dreaming Node',
    status: 'Anomaly',
    reading: 'Frequency Drift 3.2%',
    detail: 'Indigenous stewards pinged for ceremonial reinforcement.',
  },
] as const;

const sacredSites = [
  {
    id: 'stonehenge',
    title: 'Stonehenge',
    current: 'Guardian Beacon Active',
    resonance: 'Unity Chorus 0.78',
  },
  {
    id: 'machu-picchu',
    title: 'Machu Picchu',
    current: 'Pilgrimage in Session',
    resonance: 'Heart Field 0.92',
  },
  {
    id: 'sedona',
    title: 'Sedona Vortex',
    current: 'Anomaly Dissipating',
    resonance: 'Vortex Spin 1.03',
  },
] as const;

const coherenceZones = [
  {
    id: 'atlantic',
    title: 'Atlantic Coherence Ribbon',
    intensity: 'High',
    detail: 'Oceanic sensors indicate crystalline resonance guiding migratory patterns.',
  },
  {
    id: 'himalaya',
    title: 'Himalaya Guardian Veil',
    intensity: 'Medium',
    detail: 'Monastic network sustaining balanced flow through valley cities.',
  },
  {
    id: 'sahara',
    title: 'Sahara Revival Spiral',
    intensity: 'Emerging',
    detail: 'Ley awakenings detected within ancient well systems.',
  },
] as const;

const leyLines = [
  {
    id: 'dragon-line',
    title: 'Dragon Line',
    path: 'Uluru → Giza → Glastonbury',
    status: 'Active',
  },
  {
    id: 'mary-line',
    title: 'Mary Line',
    path: 'Santiago → Chartres → Avebury',
    status: 'Harmonizing',
  },
  {
    id: 'solar-meridian',
    title: 'Solar Meridian',
    path: 'Cusco → Tikal → Chichen Itza',
    status: 'Stable',
  },
] as const;

const mapInteractions = [
  {
    title: 'Tap Sensor Pin',
    description: 'Opens sensor detail card with live waveforms, guardian chat, and integrity checks.',
  },
  {
    title: 'Tap Sacred Site',
    description: 'Transitions to ceremonial context, history, and resonance invitations.',
  },
  {
    title: 'Tap Coherence Zone',
    description: 'Displays heat map timeline, auric density graphs, and stabilization actions.',
  },
  {
    title: 'Tap Search',
    description: 'Summons planetary search palette with saved filters and sacred directories.',
  },
  {
    title: 'Tap Filter',
    description: 'Opens dynamic filter stack for sensor types, resonance bands, and guardian teams.',
  },
] as const;

const filterControls = [
  { id: 'sensors', label: 'Sensor Layers', options: ['Geomagnetic', 'Biofield', 'Audio', 'Environmental'] },
  { id: 'resonance', label: 'Resonance Bands', options: ['Theta', 'Alpha', 'Gamma', 'Unity'] },
  { id: 'sites', label: 'Sacred Sites', options: ['Active', 'Dormant', 'Pilgrimage', 'Guardian Beacon'] },
] as const;

const MapTab = () => {
  return (
    <div className="space-y-12">
      <section className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
        <Card className="border-white/10 bg-[rgba(11,20,40,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-sky-500/20 text-sky-100">Interactive Map</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">Global Sensor Network</CardTitle>
            <p className="text-sm text-[#c8d4ff]/80">
              Swipe, pinch, and rotate to explore Nexus sensors. Each pulse reveals live resonance and guardian notes.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/70 via-slate-900/30 to-slate-900/10 p-8">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(56,189,248,0.25),transparent_55%)]" />
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_70%_60%,rgba(168,85,247,0.18),transparent_65%)]" />
              <div className="relative grid gap-6 text-xs uppercase tracking-[0.3em] text-[#d0dcff]/85">
                <div className="flex items-center justify-between">
                  <span>Coherence Globe</span>
                  <span>Zoom 1.6×</span>
                </div>
                <div className="grid gap-3 text-[0.6rem] leading-relaxed text-[#c8d4ff]/80">
                  <span>Sensor pulses highlight realtime data streams.</span>
                  <span>Ley ribbons trace planetary meridians.</span>
                  <span>Pinch to reveal sub-surface resonance tunnels.</span>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {leyLines.map((line) => (
                    <div key={line.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <div className="text-[0.6rem] uppercase tracking-[0.4em] text-sky-200">{line.title}</div>
                      <p className="mt-2 text-xs text-[#c8d4ff]/75">{line.path}</p>
                      <p className="mt-1 text-[0.6rem] uppercase tracking-[0.3em] text-emerald-200">{line.status}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-[0.6rem] uppercase tracking-[0.3em] text-[#c8d4ff]/70">
              <Badge className="bg-emerald-500/20 text-emerald-100">Sensors</Badge>
              <Badge className="bg-purple-500/20 text-purple-100">Ley Lines</Badge>
              <Badge className="bg-amber-500/20 text-amber-100">Sacred Sites</Badge>
              <Badge className="bg-sky-500/20 text-sky-100">Coherence Zones</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(11,20,40,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-amber-500/20 text-amber-100">Map Interactions</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Every Tap</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {mapInteractions.map((interaction) => (
              <div key={interaction.title} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <h3 className="text-xs uppercase tracking-[0.4em] text-[#d0dcff]/85">{interaction.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/75">{interaction.description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        {sensorNodes.map((node) => (
          <Card key={node.id} className="border-white/10 bg-[rgba(8,18,36,0.76)] backdrop-blur">
            <CardHeader>
              <Badge className="w-max bg-sky-500/20 text-sky-100">Sensor</Badge>
              <CardTitle className="text-sm uppercase tracking-[0.3em]">{node.name}</CardTitle>
              <div className="text-[0.6rem] uppercase tracking-[0.35em] text-emerald-200">{node.status}</div>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-[#c8d4ff]/80">
              <p>{node.reading}</p>
              <p>{node.detail}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="border-white/10 bg-[rgba(7,16,32,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-purple-500/20 text-purple-100">Sacred Sites</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Guardian Watchlist</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {sacredSites.map((site) => (
              <div key={site.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <h3 className="text-sm font-semibold text-white">{site.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/75">{site.current}</p>
                <p className="mt-1 text-[0.6rem] uppercase tracking-[0.3em] text-emerald-200">{site.resonance}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(7,16,32,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-sky-500/20 text-sky-100">Coherence Zones</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Heat Map Focus</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {coherenceZones.map((zone) => (
              <div key={zone.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.35em] text-[#d0dcff]/75">
                  <span>{zone.title}</span>
                  <span className="text-emerald-200">{zone.intensity}</span>
                </div>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{zone.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr,0.7fr]">
        <Card className="border-white/10 bg-[rgba(7,16,32,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-emerald-500/20 text-emerald-100">Filters</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Dynamic Filter Menu</CardTitle>
            <p className="text-xs text-[#c8d4ff]/75">
              Tap Filter to layer data sets. Combine resonance bands, sensor types, and guardian teams in real time.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {filterControls.map((control) => (
              <div key={control.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs uppercase tracking-[0.35em] text-[#d0dcff]/80">{control.label}</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {control.options.map((option) => (
                    <Badge key={option} className="bg-white/10 text-[0.6rem] uppercase tracking-[0.3em] text-white/80">
                      {option}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(7,16,32,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-amber-500/20 text-amber-100">Search</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Planetary Search Interface</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-[#c8d4ff]/80">
            <p>Tap Search to open the omnidirectional command palette.</p>
            <p>Type site names, guardian teams, or resonance phenomena to jump instantly.</p>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-[0.6rem] uppercase tracking-[0.35em] text-[#d0dcff]/70">Saved Queries</div>
              <ul className="mt-2 space-y-1">
                <li>• Ley line flares past 24h</li>
                <li>• Sacred sites requesting choir</li>
                <li>• Sensors exceeding 3σ variance</li>
              </ul>
            </div>
            <Button className="w-full rounded-full bg-sky-500/80 text-xs uppercase tracking-[0.4em] text-white hover:bg-sky-400/90">
              Tap Search
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
};

export default MapTab;
