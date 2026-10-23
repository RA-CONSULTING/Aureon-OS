import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const menuItems = [
  {
    id: 'settings',
    title: 'Settings & Preferences',
    description: 'Manage notifications, guardian credentials, and accessibility layers.',
    submenus: ['Notification Channels', 'Gesture Sensitivity', 'Appearance Modes'],
  },
  {
    id: 'advanced-tools',
    title: 'Advanced Tools',
    description: 'Dive into meditation modes, frequency engines, and sacred geometry viewers.',
    submenus: ['Meditation Studio', 'Frequency Generator', 'Sacred Geometry Viewer'],
  },
  {
    id: 'guardian-network',
    title: 'Guardian Network',
    description: 'Coordinate with global stewards, access mission logs, and join resonance rooms.',
    submenus: ['Mission Briefings', 'Resonance Rooms', 'Council Broadcasts'],
  },
  {
    id: 'archives',
    title: 'Archives & Scrolls',
    description: 'Browse codices, ritual histories, and recorded transmissions.',
    submenus: ['Sacred Scrolls', 'Chronicle Playback', 'Audio Archives'],
  },
] as const;

const advancedModules = [
  {
    id: 'meditation-mode',
    title: 'Meditation Mode',
    summary: 'Immersive breath pacing, visual mandalas, and biofeedback loops tailor-made for calm.',
    action: 'Launch Meditation Mode',
  },
  {
    id: 'frequency-engine',
    title: 'Frequency Generator',
    summary: 'Compose custom harmonic stacks. Blend 432Hz heart fields with binaural carriers.',
    action: 'Start Frequency Session',
  },
  {
    id: 'geometry-viewer',
    title: 'Sacred Geometry Viewer',
    summary: 'Rotate merkaba, flower of life, and 64-tetrahedron grid in responsive 3D.',
    action: 'Open Geometry Viewer',
  },
  {
    id: 'guardian-ritual',
    title: 'Guardian Ritual Library',
    summary: 'Stream ceremonial protocols, chant libraries, and planetary guardianship rites.',
    action: 'View Ritual Library',
  },
] as const;

const notifications = [
  { id: 'anomaly', label: 'Anomalies', detail: 'Control frequency, severity thresholds, escalation guardians.' },
  { id: 'patterns', label: 'Patterns', detail: 'Toggle AI pattern highlights for map, dashboard, and insights.' },
  { id: 'milestones', label: 'Coherence Milestones', detail: 'Celebrate achievements with guardian circles + badges.' },
  { id: 'sacred-sites', label: 'Sacred Sites', detail: 'Receive invitations when beacons activate or ceremonies begin.' },
] as const;

const interactions = [
  {
    title: 'Tap Menu Item',
    description: 'Opens the corresponding page or tool instantly, keeping live feed in background awareness.',
  },
  {
    title: 'Tap Submenu',
    description: 'Reveals nested options for deeper configuration without leaving the More tab.',
  },
] as const;

const MoreTab = () => {
  return (
    <div className="space-y-12">
      <section className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
        <Card className="border-white/10 bg-[rgba(10,18,38,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-sky-500/20 text-sky-100">More Menu</Badge>
            <CardTitle className="text-lg uppercase tracking-[0.3em]">Settings & Advanced Features</CardTitle>
            <p className="text-sm text-[#c8d4ff]/80">
              Navigate to every deep system layer—advanced tools, guardian network, archives, and precision settings.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {menuItems.map((item) => (
              <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.35em] text-[#d0dcff]/75">
                  <span>{item.title}</span>
                  <Button className="rounded-full bg-emerald-500/80 px-4 py-1 text-[0.55rem] uppercase tracking-[0.35em] text-white hover:bg-emerald-400/90">
                    Tap Menu Item
                  </Button>
                </div>
                <p className="mt-3 text-xs text-[#c8d4ff]/80">{item.description}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.submenus.map((submenu) => (
                    <Button
                      key={submenu}
                      variant="outline"
                      className="rounded-full border-white/20 bg-transparent px-3 py-1 text-[0.55rem] uppercase tracking-[0.35em] text-[#d0dcff]/80"
                    >
                      Tap Submenu · {submenu}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(10,18,38,0.76)] backdrop-blur">
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

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="border-white/10 bg-[rgba(8,16,34,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-purple-500/20 text-purple-100">Advanced Tools</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Launchpad</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {advancedModules.map((module) => (
              <div key={module.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <h3 className="text-sm font-semibold text-white">{module.title}</h3>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{module.summary}</p>
                <Button className="mt-3 w-full rounded-full bg-sky-500/80 text-[0.6rem] uppercase tracking-[0.35em] text-white hover:bg-sky-400/90">
                  {module.action}
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-[rgba(8,16,34,0.76)] backdrop-blur">
          <CardHeader>
            <Badge className="w-max bg-amber-500/20 text-amber-100">Notifications</Badge>
            <CardTitle className="text-sm uppercase tracking-[0.3em]">Channel Matrix</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {notifications.map((notification) => (
              <div key={notification.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="text-xs uppercase tracking-[0.35em] text-[#d0dcff]/75">{notification.label}</div>
                <p className="mt-2 text-xs text-[#c8d4ff]/80">{notification.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
};

export default MoreTab;
