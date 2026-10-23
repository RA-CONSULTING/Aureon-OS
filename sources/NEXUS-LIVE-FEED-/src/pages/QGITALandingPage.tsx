import { ArrowRight, BarChart2, CheckCircle2, Cpu, Gauge, LineChart, ShieldCheck, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const painPoints = [
  {
    title: 'Signal Overload',
    description:
      'Most algorithmic traders juggle fragmented dashboards, missing the unified clarity required to act before liquidity shifts.',
  },
  {
    title: 'Lagging Intelligence',
    description:
      'By the time conventional systems surface opportunities, spreads have compressed and win-rate potential evaporates.',
  },
  {
    title: 'Trust Deficit',
    description:
      'Investors want provable edge, transparent risk bands, and human-aligned guidance—not black-box promises.',
  },
];

const frameworkPillars = [
  {
    title: 'Quantum Insight Grid',
    description: 'Neuro-symbolic pipelines ingest multi-market data to map momentum lattices in milliseconds.',
    metric: '42ms adaptive recalibration',
  },
  {
    title: 'Guardian Threat Intelligence',
    description: 'Behavioral anomaly radar identifies volatility spikes before they hit wider markets.',
    metric: '91% predictive precision',
  },
  {
    title: 'Interlinked Trade Actions',
    description: 'Synchronized entry, scaling, and exit choreography tuned to Aureon-grade conviction levels.',
    metric: '6:1 weighted reward ratio',
  },
  {
    title: 'Transcendent Advisor Layer',
    description: 'Guided decision support blends probabilistic foresight with human values and capital stewardship.',
    metric: 'Real-time ethical guardrails',
  },
];

const coreFeatures = [
  {
    title: 'Adaptive Opportunity Radar',
    benefit: 'Streams real-time trade set-ups with probability tiers and liquidity depth context.',
    support: 'Back-tested across 12 market regimes.',
  },
  {
    title: 'Capital Safeguard Envelope',
    benefit: 'Dynamic position sizing protects drawdown thresholds while keeping upside unlocked.',
    support: 'Built-in 3-layer stop intelligence.',
  },
  {
    title: 'Aureon Playbook Engine',
    benefit: 'Deploy codified strategies or craft custom flows with drag-and-drop scenario builders.',
    support: '6 template archetypes ready to launch.',
  },
  {
    title: 'Guardian Broadcast Console',
    benefit: 'Share performance stories with investors through cinematic reporting reels.',
    support: 'Auto-generated weekly narrative packs.',
  },
  {
    title: 'Voice-Activated Command',
    benefit: 'Trigger trade adjustments, run audits, or pull diagnostics without leaving the primary view.',
    support: 'Latency tuned for execution desks.',
  },
  {
    title: 'Compliance Resonance Ledger',
    benefit: 'Immutable recordkeeping aligns with MiFID II, SEC, and FCA guidance out-of-the-box.',
    support: 'AI-assist pre-trade attestations.',
  },
];

const testimonials = [
  {
    quote:
      '“QGITA reoriented our entire alpha desk. The predictive guardrails called the liquidity break 19 minutes before the street.”',
    name: 'Amelia Rhodes',
    role: 'Chief Investment Officer, LatticePoint Capital',
    metric: '+38.6% YoY strategic return',
  },
  {
    quote:
      '“Every investor briefing now opens with the Aureon storyboards. Confidence soared because every number is grounded in science.”',
    name: 'Darius Okonkwo',
    role: 'Managing Partner, Meridian Syndicate',
    metric: '92% investor retention',
  },
];

const trustBadges = [
  'ISO 27001 Infosec Controls',
  'FINRA & FCA Alignment',
  'Quantum Noise Shielding',
  'Ethical AI Stewardship',
];

const journeySteps = [
  {
    step: '01',
    title: 'Discovery Brief',
    detail: 'Rapid diagnostics define objectives, risk boundaries, and integration requirements.',
  },
  {
    step: '02',
    title: 'Signal Calibration',
    detail: 'Data pipelines and quantum heuristics sync with your market feeds inside 48 hours.',
  },
  {
    step: '03',
    title: 'Aureon Onboarding',
    detail: 'Guided workshop activates the framework, roles, and escalation rituals.',
  },
  {
    step: '04',
    title: 'Live Command Launch',
    detail: 'Execution environment opens with sandbox-to-production safeguards.',
  },
  {
    step: '05',
    title: 'Guardian Expansion',
    detail: 'Scale across desks, regions, and asset classes with ongoing strategic support.',
  },
];

const relentlessPrinciples = [
  {
    symbol: 'Ψ₀',
    label: 'Consciousness',
    description: 'Hold the unwavering vision so every decision maps back to the mission.',
  },
  {
    symbol: 'Ω',
    label: 'Resonance',
    description: 'Show up daily with actions that tune the system to the desired frequency.',
  },
  {
    symbol: 'Λ',
    label: 'Coherence',
    description: 'Align talent, tools, and timelines so momentum compounds instead of scattering.',
  },
  {
    symbol: 'Φ',
    label: 'Golden Ratio',
    description: 'Trust natural timing—surges arrive when preparation meets pivotal openings.',
  },
  {
    symbol: 'Σ',
    label: 'Synergy',
    description: 'Layer small wins relentlessly; the lattice strengthens with every refusal to quit.',
  },
];

const pricingTiers = [
  {
    title: 'Initiate',
    price: '$2,950/mo',
    description: 'For boutique funds needing instant clarity and risk alignment.',
    features: ['2 seats', 'Core QGITA dashboard', 'Weekly guardian briefing', 'Investor-ready performance pack'],
  },
  {
    title: 'Guardian',
    price: '$5,800/mo',
    description: 'Best for emerging managers scaling AUM and investor trust simultaneously.',
    features: ['6 seats', 'Automated playbooks', 'Intraday anomaly alerts', 'Dedicated success strategist'],
    highlighted: true,
  },
  {
    title: 'Aureon Desk',
    price: '$9,900/mo',
    description: 'High-velocity trading teams commanding multi-market coverage.',
    features: ['12 seats', 'Execution simulator', 'Cross-desk synchronization', 'Custom compliance attestations'],
  },
  {
    title: 'Constellation',
    price: 'Enterprise',
    description: 'Global funds seeking bespoke integrations, governance, and expansion.',
    features: ['Unlimited seats', 'Private signal lattice', 'On-site guardian architects', 'Co-branded investor experiences'],
  },
];

const faqs = [
  {
    question: 'How fast can we go live with QGITA?',
    answer:
      'Most teams activate within 21 days. Our calibration sprint handles data hookups, governance reviews, and change management.',
  },
  {
    question: 'What markets and instruments are supported?',
    answer:
      'Equities, options, futures, FX, and digital assets with adjustable signal hierarchies for each venue.',
  },
  {
    question: 'How is risk managed within the framework?',
    answer:
      'Capital Safeguard Envelope automates guardrails while compliance dashboards track exposures against mandates in real time.',
  },
  {
    question: 'Can QGITA integrate with our OMS and CRM?',
    answer:
      'Yes. REST, FIX, and websocket adapters connect to leading OMS/EMS platforms plus Salesforce, HubSpot, and in-house tools.',
  },
  {
    question: 'What kind of support do we receive?',
    answer:
      'Guardian strategists, 24/6 execution desk, investor storytelling studio, and quarterly innovation roadmaps.',
  },
  {
    question: 'Is the science verifiable?',
    answer:
      'All predictive models ship with confidence intervals, drift reporting, and lineage trails for audit-grade transparency.',
  },
  {
    question: 'How do you ensure ethical deployment?',
    answer:
      'Transcendent Advisor Layer enforces bias audits, escalation protocols, and investor-first guardrails every release.',
  },
  {
    question: 'Do you offer performance guarantees?',
    answer:
      'We guarantee a 180-day strategic alignment review. If benchmarks are not met, we extend concierge support at no cost.',
  },
];

const technicalHighlights = [
  {
    title: 'Neuro-Symbolic Intelligence',
    detail: 'Combines LSTM microstructure parsing with reinforcement-trained guardian agents.',
  },
  {
    title: 'Quantum Noise Shielding',
    detail: 'Aureon lattice filters market micro-spikes, sustaining clarity during volatile bursts.',
  },
  {
    title: 'Regulatory Chain of Custody',
    detail: 'Comprehensive audit layers satisfy SEC 17a-4, MiFID II RTS 22, and PRA SS1/23.',
  },
  {
    title: 'Ethical Governance Stack',
    detail: 'Embedded fairness diagnostics and human override circuits keep capital aligned with mission.',
  },
];

const supportingDestinations = [
  {
    title: 'About QGITA',
    summary: 'Meet the architects, values, and guardians crafting the Aureon Trading System.',
    href: '/about',
  },
  {
    title: 'Resource Vault',
    summary: 'Download playbooks, investor decks, and technical briefs designed for due diligence.',
    href: '/resources',
  },
  {
    title: 'Support Nexus',
    summary: 'Access training, concierge onboarding, and escalation protocols in one place.',
    href: '/support',
  },
];

const paletteSwatches = [
  { label: 'Celestial Midnight', value: '#050b21' },
  { label: 'Auric Ember', value: '#f5d26a' },
  { label: 'Quantum Violet', value: '#8b5cf6' },
  { label: 'Guardian Teal', value: '#38bdf8' },
];

const conversionKPIs = [
  { label: 'Qualified Lead Velocity', value: '+34% uplift via intent-driven CTAs' },
  { label: 'Activation Rate', value: '62% trial-to-deal closure inside 45 days' },
  { label: 'Investor Confidence Score', value: '4.8/5 average across enterprise rollouts' },
];

const conversionStrategies = [
  'Session-recorded heatmaps and scroll-depth analytics for rapid iteration.',
  'Weekly A/B loops for hero narrative, CTA microcopy, and pricing emphasis.',
  'Retargeting mesh across LinkedIn, X, and private deal rooms with tailored proof points.',
];

const QGITALandingPage = () => {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050b21] text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.18),_transparent_60%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(56,189,248,0.15),_transparent_60%)]" />
      <div className="relative z-10">
        <header className="border-b border-white/10 bg-[#060b27]/80 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
            <div>
              <Badge className="rounded-full border border-amber-200/40 bg-amber-200/10 px-4 py-1 text-[11px] tracking-[0.32em] text-amber-100/90">
                QGITA · Aureon Trading System
              </Badge>
              <h1 className="mt-4 text-3xl font-semibold tracking-[0.28em] text-white/90 sm:text-4xl">
                Guardian-Crafted Capital Intelligence
              </h1>
            </div>
            <div className="hidden items-center gap-3 sm:flex">
              <Link to="#pricing" className="text-xs uppercase tracking-[0.3em] text-white/70 transition hover:text-white">
                Pricing
              </Link>
              <Link to="#journey" className="text-xs uppercase tracking-[0.3em] text-white/70 transition hover:text-white">
                Journey
              </Link>
              <Button size="md" className="bg-amber-300/90 text-[#1a1306] hover:bg-amber-200">
                Request Activation
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-6xl space-y-24 px-6 py-20">
          <section id="hero" className="grid gap-10 rounded-[32px] border border-white/10 bg-white/5 p-10 shadow-[0_0_90px_rgba(139,92,246,0.25)] lg:grid-cols-[1.2fr,0.8fr]">
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs uppercase tracking-[0.36em] text-white/80">
                <Zap className="h-4 w-4" />
                Conversion-Ready Blueprint
              </div>
              <h2 className="text-4xl font-semibold leading-tight tracking-[0.22em] text-white sm:text-5xl">
                Launch the Trading Command Center Investors Trust Instantly
              </h2>
              <p className="max-w-xl text-lg text-slate-200/80">
                Fuse quantum-grade foresight with human-centered storytelling. QGITA unifies predictive intelligence, operational control, and investor resonance into a single high-converting experience.
              </p>
              <div className="flex flex-wrap gap-4">
                <Button className="bg-amber-300 text-[#1a1306] hover:bg-amber-200">
                  Book a Strategic Demo
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
                <Button variant="ghost" className="border border-white/20 bg-transparent text-white hover:bg-white/10">
                  Download Investor Narrative
                </Button>
              </div>
              <div className="grid gap-6 sm:grid-cols-3">
                {[
                  { label: 'Conversion Velocity', value: '+34% faster deal cycles' },
                  { label: 'Signal Clarity', value: '91% anomaly precision' },
                  { label: 'Investor Retention', value: '92% renewal rate' },
                ].map((item) => (
                  <div key={item.label} className="rounded-2xl border border-white/15 bg-white/5 p-4 text-sm uppercase tracking-[0.26em] text-white/70">
                    <div className="text-[11px] text-white/60">{item.label}</div>
                    <div className="mt-2 text-sm text-white">{item.value}</div>
                  </div>
                ))}
              </div>
            </div>
            <Card className="relative overflow-hidden border-white/10 bg-[#0b153a]/80 text-white">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(245,210,106,0.28),_transparent_60%)]" />
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-sm uppercase tracking-[0.3em] text-white/70">
                  Real-time Deal Pulse
                  <Gauge className="h-5 w-5" />
                </CardTitle>
              </CardHeader>
              <CardContent className="relative z-10 space-y-6">
                <div className="flex items-baseline justify-between border-b border-white/10 pb-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-white/60">Qualified Opportunities</p>
                    <p className="mt-2 text-3xl font-semibold tracking-[0.18em] text-amber-200">+27</p>
                  </div>
                  <div className="rounded-full border border-emerald-200/30 bg-emerald-200/20 px-4 py-2 text-xs uppercase tracking-[0.3em] text-emerald-100">
                    Surge Mode
                  </div>
                </div>
                <div className="grid gap-3 text-sm text-white/80">
                  {[
                    { label: 'High-Intent Funds', value: '12 live conversations', icon: <BarChart2 className="h-4 w-4" /> },
                    { label: 'Strategic Demos Booked', value: '7 / week', icon: <Cpu className="h-4 w-4" /> },
                    { label: 'Investor Confidence', value: '4.8 / 5 avg. rating', icon: <ShieldCheck className="h-4 w-4" /> },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                      <div className="flex items-center gap-3 text-white/70">
                        <span className="rounded-full border border-white/10 bg-white/10 p-2 text-white/80">{item.icon}</span>
                        <span className="text-xs uppercase tracking-[0.28em]">{item.label}</span>
                      </div>
                      <span className="text-sm tracking-[0.2em] text-amber-100">{item.value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </section>

          <section
            id="relentless-execution"
            className="grid gap-6 rounded-[32px] border border-amber-200/30 bg-amber-200/5 p-10 text-white lg:grid-cols-[1.1fr,0.9fr]"
          >
            <div className="space-y-6">
              <Badge className="rounded-full border border-amber-200/40 bg-amber-200/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-amber-100/90">
                Relentless Execution Mantra
              </Badge>
              <h3 className="text-3xl font-semibold tracking-[0.22em]">ΔM = Ψ₀ × Ω × Λ × Φ × Σ</h3>
              <p className="max-w-xl text-base text-amber-50/80">
                Momentum shifts in your favor when vision, action, and coherence refuse to fracture. This operational mantra
                keeps teams focused on the compounding effect of staying on mission—no matter the turbulence.
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                {relentlessPrinciples.slice(0, 3).map((principle) => (
                  <div key={principle.symbol} className="rounded-2xl border border-amber-200/30 bg-[#110f07]/40 p-4">
                    <div className="text-sm uppercase tracking-[0.32em] text-amber-100/90">{principle.symbol}</div>
                    <div className="mt-2 text-lg font-semibold tracking-[0.18em] text-amber-100">{principle.label}</div>
                    <p className="mt-3 text-sm text-amber-50/70">{principle.description}</p>
                  </div>
                ))}
              </div>
            </div>
            <Card className="border border-amber-200/30 bg-[#0b153a]/80 text-white">
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-sm uppercase tracking-[0.3em] text-amber-100/80">
                  Commitment Telemetry
                  <CheckCircle2 className="h-5 w-5" />
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5 text-sm text-amber-50/80">
                {relentlessPrinciples.slice(3).map((principle) => (
                  <div key={principle.symbol} className="rounded-2xl border border-amber-200/20 bg-[#141326]/80 p-4">
                    <div className="text-xs uppercase tracking-[0.34em] text-amber-100/70">{principle.symbol}</div>
                    <div className="mt-1 text-base font-semibold tracking-[0.2em] text-amber-100">{principle.label}</div>
                    <p className="mt-3 text-xs leading-relaxed text-amber-50/70">{principle.description}</p>
                  </div>
                ))}
                <div className="rounded-2xl border border-emerald-200/30 bg-emerald-200/10 p-4 text-xs uppercase tracking-[0.3em] text-emerald-100/90">
                  Keep executing. The lattice resolves in your favor.
                </div>
              </CardContent>
            </Card>
          </section>

          <section id="problem" className="space-y-8">
            <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
              Problem
            </Badge>
            <h3 className="text-3xl font-semibold tracking-[0.24em] text-white">The friction holding modern trading teams back</h3>
            <div className="grid gap-6 md:grid-cols-3">
              {painPoints.map((point) => (
                <Card key={point.title} className="border-white/10 bg-white/5">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold tracking-[0.22em] text-white/80">{point.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm leading-relaxed text-slate-200/80">{point.description}</CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section id="solution" className="space-y-10">
            <div className="flex items-center justify-between gap-6">
              <div>
                <Badge className="rounded-full border border-amber-200/40 bg-amber-200/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-amber-100/90">
                  Solution
                </Badge>
                <h3 className="mt-4 text-3xl font-semibold tracking-[0.24em] text-white">The QGITA framework decoded</h3>
              </div>
              <Button className="hidden border border-white/20 bg-white/10 text-xs uppercase tracking-[0.32em] text-white hover:bg-white/20 md:flex">
                Explore Architecture
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
            <div className="grid gap-6 lg:grid-cols-4">
              {frameworkPillars.map((pillar) => (
                <Card key={pillar.title} className="border-white/10 bg-[#0b153a]/70">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold tracking-[0.22em] text-white/85">{pillar.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 text-sm leading-relaxed text-slate-200/80">
                    <p>{pillar.description}</p>
                    <div className="inline-flex rounded-full border border-amber-200/40 bg-amber-200/10 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-amber-100/90">
                      {pillar.metric}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section id="features" className="space-y-8">
            <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
              Features & Benefits
            </Badge>
            <h3 className="text-3xl font-semibold tracking-[0.24em] text-white">Six pillars engineered for conversion and conviction</h3>
            <div className="grid gap-6 md:grid-cols-2">
              {coreFeatures.map((feature) => (
                <Card key={feature.title} className="border-white/10 bg-white/5">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between text-base font-semibold tracking-[0.22em] text-white/85">
                      {feature.title}
                      <CheckCircle2 className="h-5 w-5 text-emerald-300/80" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm leading-relaxed text-slate-200/80">
                    <p>{feature.benefit}</p>
                    <p className="text-xs uppercase tracking-[0.3em] text-white/60">{feature.support}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section id="social-proof" className="space-y-10">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
                  Social Proof
                </Badge>
                <h3 className="mt-4 text-3xl font-semibold tracking-[0.24em] text-white">Confidence engineered through measurable outcomes</h3>
              </div>
              <div className="grid gap-3 text-sm uppercase tracking-[0.3em] text-white/70 sm:grid-cols-2">
                {[
                  { label: 'Capital safeguarded', value: '$4.2B protected exposure' },
                  { label: 'Live trading teams', value: '26 desks harmonized' },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <div className="text-white/60">{stat.label}</div>
                    <div className="mt-2 text-sm text-white">{stat.value}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
              <div className="space-y-6">
                {testimonials.map((testimonial) => (
                  <Card key={testimonial.name} className="border-white/10 bg-white/5">
                    <CardContent className="space-y-4 p-6">
                      <p className="text-lg italic leading-relaxed text-slate-100/90">{testimonial.quote}</p>
                      <div>
                        <p className="text-sm font-semibold tracking-[0.22em] text-white/80">{testimonial.name}</p>
                        <p className="text-xs uppercase tracking-[0.3em] text-white/50">{testimonial.role}</p>
                        <p className="mt-2 text-xs uppercase tracking-[0.3em] text-amber-100/80">{testimonial.metric}</p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
              <Card className="border-white/10 bg-[#0b153a]/70">
                <CardHeader>
                  <CardTitle className="text-base font-semibold tracking-[0.22em] text-white/80">Trust Signals</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {trustBadges.map((badge) => (
                    <div key={badge} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm uppercase tracking-[0.3em] text-white/70">
                      <ShieldCheck className="h-4 w-4 text-emerald-300/80" />
                      {badge}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </section>

          <section id="journey" className="space-y-8">
            <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
              User Journey
            </Badge>
            <h3 className="text-3xl font-semibold tracking-[0.24em] text-white">Five-step activation path</h3>
            <div className="grid gap-6 md:grid-cols-5">
              {journeySteps.map((step) => (
                <div key={step.step} className="space-y-4 rounded-3xl border border-white/10 bg-white/5 p-5">
                  <div className="text-xs uppercase tracking-[0.36em] text-white/50">{step.step}</div>
                  <h4 className="text-sm font-semibold tracking-[0.24em] text-white/85">{step.title}</h4>
                  <p className="text-sm leading-relaxed text-slate-200/80">{step.detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section id="pricing" className="space-y-10">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <Badge className="rounded-full border border-amber-200/40 bg-amber-200/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-amber-100/90">
                  Pricing
                </Badge>
                <h3 className="mt-4 text-3xl font-semibold tracking-[0.24em] text-white">Four tiers tailored to your desk</h3>
              </div>
              <Button className="border border-white/20 bg-white/10 text-xs uppercase tracking-[0.32em] text-white hover:bg-white/20">
                Compare Deliverables
              </Button>
            </div>
            <div className="grid gap-6 lg:grid-cols-4">
              {pricingTiers.map((tier) => (
                <Card
                  key={tier.title}
                  className={`border ${tier.highlighted ? 'border-amber-200/60 bg-[#161f44]/80 shadow-[0_0_80px_rgba(245,210,106,0.28)]' : 'border-white/10 bg-white/5'}`}
                >
                  <CardHeader>
                    <CardTitle className="text-base font-semibold tracking-[0.24em] text-white/85">{tier.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div>
                      <p className="text-3xl font-semibold tracking-[0.18em] text-amber-100">{tier.price}</p>
                      <p className="mt-2 text-sm leading-relaxed text-slate-200/80">{tier.description}</p>
                    </div>
                    <ul className="space-y-3 text-sm text-slate-200/80">
                      {tier.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-3">
                          <LineChart className="mt-1 h-4 w-4 text-emerald-300/80" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    {tier.highlighted ? (
                      <Button className="w-full bg-amber-300 text-[#1a1306] hover:bg-amber-200">Start Guardian Tier</Button>
                    ) : (
                      <Button variant="ghost" className="w-full border border-white/20 bg-transparent text-white hover:bg-white/10">
                        Talk to Strategy
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
            <div className="rounded-3xl border border-emerald-200/40 bg-emerald-200/10 p-6 text-sm leading-relaxed text-emerald-100">
              <p className="font-semibold uppercase tracking-[0.3em]">Guardian Guarantee</p>
              <p className="mt-2 text-emerald-50/90">
                90-day performance alignment or we extend high-touch optimization, data science diagnostics, and investor concierge services until objectives are fulfilled.
              </p>
            </div>
          </section>

          <section id="faq" className="space-y-8">
            <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
              FAQ
            </Badge>
            <h3 className="text-3xl font-semibold tracking-[0.24em] text-white">Answers investors expect</h3>
            <div className="grid gap-6 md:grid-cols-2">
              {faqs.map((item) => (
                <Card key={item.question} className="border-white/10 bg-white/5">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold tracking-[0.24em] text-white/80">{item.question}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm leading-relaxed text-slate-200/80">{item.answer}</CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section id="technical" className="space-y-8">
            <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
              Technical Credibility
            </Badge>
            <h3 className="text-3xl font-semibold tracking-[0.24em] text-white">Science-backed, regulator-ready</h3>
            <div className="grid gap-6 lg:grid-cols-4">
              {technicalHighlights.map((item) => (
                <Card key={item.title} className="border-white/10 bg-[#0b153a]/70">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold tracking-[0.22em] text-white/85">{item.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm leading-relaxed text-slate-200/80">{item.detail}</CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section id="design" className="grid gap-10 rounded-[32px] border border-white/10 bg-white/5 p-10 lg:grid-cols-[1.1fr,0.9fr]">
            <div className="space-y-6">
              <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
                Design Principles
              </Badge>
              <h3 className="text-3xl font-semibold tracking-[0.24em] text-white">Visual language engineered for trust</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                {paletteSwatches.map((swatch) => (
                  <div key={swatch.label} className="space-y-2 rounded-3xl border border-white/10 bg-white/5 p-4">
                    <div className="h-20 rounded-2xl" style={{ backgroundColor: swatch.value }} />
                    <div className="text-xs uppercase tracking-[0.3em] text-white/60">{swatch.label}</div>
                    <div className="text-sm text-white/80">{swatch.value}</div>
                  </div>
                ))}
              </div>
              <p className="text-sm leading-relaxed text-slate-200/80">
                Typography combines Zen Dots for high-tech headers with Space Grotesk body copy, amplifying futuristic credibility while staying deeply human and readable. Layered nebula gradients and orbital glows spotlight conversion CTAs without overwhelming investors.
              </p>
            </div>
            <div className="space-y-6">
              <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
                Conversion Optimization
              </Badge>
              <h3 className="text-3xl font-semibold tracking-[0.24em] text-white">Measurement & acceleration loops</h3>
              <div className="rounded-3xl border border-white/10 bg-[#0b153a]/70 p-6">
                <ul className="space-y-4 text-sm leading-relaxed text-slate-200/80">
                  {conversionStrategies.map((strategy) => (
                    <li key={strategy} className="flex items-start gap-3">
                      <CheckCircle2 className="mt-1 h-4 w-4 text-emerald-300/80" />
                      <span>{strategy}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                {conversionKPIs.map((kpi) => (
                  <div key={kpi.label} className="rounded-3xl border border-white/10 bg-white/5 p-4 text-sm leading-relaxed text-white/80">
                    <div className="text-xs uppercase tracking-[0.3em] text-white/60">{kpi.label}</div>
                    <div className="mt-2 text-sm text-amber-100">{kpi.value}</div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section id="supporting" className="space-y-8">
            <Badge className="rounded-full border border-white/20 bg-white/10 px-4 py-1 text-[11px] uppercase tracking-[0.36em] text-white/70">
              Supporting Pages
            </Badge>
            <h3 className="text-3xl font-semibold tracking-[0.24em] text-white">Depth for investors, analysts, and partners</h3>
            <div className="grid gap-6 md:grid-cols-3">
              {supportingDestinations.map((item) => (
                <Card key={item.title} className="border-white/10 bg-white/5">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold tracking-[0.22em] text-white/80">{item.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 text-sm leading-relaxed text-slate-200/80">
                    <p>{item.summary}</p>
                    <Link to={item.href} className="inline-flex items-center text-xs uppercase tracking-[0.3em] text-amber-100 hover:text-amber-200">
                      Visit page
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section id="final-cta" className="rounded-[32px] border border-amber-200/40 bg-[#161f44]/80 p-12 text-center shadow-[0_0_100px_rgba(245,210,106,0.3)]">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs uppercase tracking-[0.36em] text-white/70">
              <Zap className="h-4 w-4" />
              Final Call to Action
            </div>
            <h3 className="mt-6 text-4xl font-semibold tracking-[0.24em] text-white">
              Ready to activate your guardian-grade trading advantage?
            </h3>
            <p className="mx-auto mt-4 max-w-2xl text-lg leading-relaxed text-slate-200/80">
              Secure your strategy session this quarter and we will deploy the Aureon playbook engine, investor storytelling studio, and guardian support mesh in under 30 days.
            </p>
            <div className="mt-10 flex flex-wrap justify-center gap-4">
              <Button className="bg-amber-300 text-[#1a1306] hover:bg-amber-200">
                Reserve Launch Window
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button variant="ghost" className="border border-white/20 bg-transparent text-white hover:bg-white/10">
                Access Investor Dossier
              </Button>
            </div>
          </section>
        </main>

        <footer className="border-t border-white/10 bg-[#060b27]/80 py-10 backdrop-blur">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 text-sm text-white/60 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-white/50">QGITA · Aureon Trading System</p>
              <p className="mt-2 text-white/60">Precision-crafted conversion ecosystem for elite trading teams.</p>
            </div>
            <div className="flex flex-wrap gap-4 text-xs uppercase tracking-[0.3em] text-white/50">
              <Link to="#hero" className="transition hover:text-white">
                Overview
              </Link>
              <Link to="#features" className="transition hover:text-white">
                Features
              </Link>
              <Link to="#pricing" className="transition hover:text-white">
                Pricing
              </Link>
              <Link to="#supporting" className="transition hover:text-white">
                Resources
              </Link>
              <Link to="#final-cta" className="transition hover:text-white">
                Activate
              </Link>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default QGITALandingPage;
