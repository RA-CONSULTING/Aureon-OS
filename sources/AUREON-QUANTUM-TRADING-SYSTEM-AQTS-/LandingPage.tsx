import React from 'react';

type LandingPageProps = {
  onStartTrading: () => void;
};

type Feature = {
  title: string;
  description: string;
  icon: string;
  gradient: string;
  iconGradient: string;
};

type Pillar = {
  title: string;
  description: string;
  points: string[];
};

const features: Feature[] = [
  {
    title: 'AI-Powered Analysis',
    description:
      'Advanced machine intelligence fused with QGITA geometry to isolate high-probability structural inflections before the market reacts.',
    icon: '🤖',
    gradient: 'from-fuchsia-600/20 via-purple-700/30 to-indigo-800/30',
    iconGradient: 'from-fuchsia-400 via-purple-500 to-indigo-500',
  },
  {
    title: 'Quantum Speed',
    description:
      'Execute trades with millisecond responsiveness across top-tier exchanges using optimized smart-order routing.',
    icon: '⚡',
    gradient: 'from-blue-600/20 via-sky-700/30 to-cyan-800/30',
    iconGradient: 'from-sky-400 via-blue-500 to-cyan-500',
  },
  {
    title: 'Bank-Level Security',
    description:
      'Encrypted key management, IP allowlisting, and per-trade risk controls ensure capital preservation in every scenario.',
    icon: '🛡️',
    gradient: 'from-emerald-600/20 via-teal-700/30 to-slate-800/30',
    iconGradient: 'from-emerald-400 via-teal-500 to-sky-500',
  },
  {
    title: 'Predictive Analytics',
    description:
      'Multi-timeframe coherence scoring, volume anomalies, and sentiment synthesis converge into a single actionable signal.',
    icon: '📈',
    gradient: 'from-amber-600/20 via-orange-700/30 to-rose-800/30',
    iconGradient: 'from-amber-400 via-orange-500 to-rose-500',
  },
];

const pillars: Pillar[] = [
  {
    title: 'Fibonacci Time Lattice',
    description:
      'Curvature-aware time series modelling reveals hidden pressure waves and structural transitions before conventional indicators.',
    points: [
      'Golden-ratio aligned event scanning',
      'Adaptive curvature thresholds per asset',
      'Cross-timeframe resonance detection',
    ],
  },
  {
    title: 'Lighthouse Consensus',
    description:
      'Five-metric validation engine that blends linear, non-linear, and geometric coherence to eliminate false positives.',
    points: [
      'MACD & volatility convergence',
      'Volume anomaly detection',
      'Self-similarity confirmation across scales',
    ],
  },
  {
    title: 'Autonomous Execution',
    description:
      'Risk-aware trade orchestration with circuit breakers, drawdown guardrails, and multi-exchange liquidity routing.',
    points: [
      '2% max capital exposure per position',
      'Dynamic stop-loss & take-profit bands',
      'Full audit trail with instant notifications',
    ],
  },
];

const metrics = [
  { label: 'Signal Precision', value: '92%' },
  { label: 'Avg. ROI Improvement', value: '24%' },
  { label: 'Latency', value: '< 120ms' },
];

const LandingPage: React.FC<LandingPageProps> = ({ onStartTrading }) => {
  return (
    <div className="min-h-screen bg-[#080921] text-slate-100">
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-32 top-[-8rem] h-[26rem] w-[26rem] rounded-full bg-purple-600/40 blur-3xl" />
          <div className="absolute right-[-10rem] top-24 h-[28rem] w-[28rem] rounded-full bg-sky-500/30 blur-[140px]" />
          <div className="absolute left-1/2 top-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500/20 blur-[120px]" />
        </div>

        <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-8">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 via-indigo-500 to-sky-500 text-lg font-semibold text-white shadow-lg shadow-purple-500/40">
              AQ
            </span>
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-slate-400">Aureon</p>
              <p className="text-lg font-semibold text-white">Quantum Trading System</p>
            </div>
          </div>

          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-300 lg:flex">
            <a className="transition hover:text-white" href="#features">
              Features
            </a>
            <a className="transition hover:text-white" href="#technology">
              Technology
            </a>
            <a className="transition hover:text-white" href="#pricing">
              Pricing
            </a>
            <a className="transition hover:text-white" href="#support">
              Support
            </a>
          </nav>

          <button
            onClick={onStartTrading}
            className="hidden rounded-full bg-gradient-to-r from-fuchsia-500 via-purple-500 to-indigo-500 px-6 py-2 text-sm font-semibold shadow-lg shadow-purple-500/40 transition hover:shadow-purple-400/50 lg:inline-flex"
          >
            Get Started
          </button>
        </header>

        <main className="relative z-10">
          <section className="mx-auto flex max-w-5xl flex-col items-center px-6 pb-24 pt-16 text-center md:pt-24">
            <span className="rounded-full border border-purple-400/40 bg-purple-500/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-purple-200">
              Quantum Trading Redefined
            </span>
            <h1 className="mt-6 max-w-4xl text-4xl font-bold leading-tight text-white md:text-5xl lg:text-6xl">
              Harness the <span className="text-transparent bg-gradient-to-r from-purple-400 via-fuchsia-300 to-sky-300 bg-clip-text">power of QGITA</span> to anticipate the market before it moves.
            </h1>
            <p className="mt-6 max-w-3xl text-lg text-slate-300 md:text-xl">
              Experience unprecedented accuracy, speed, and risk control. AQTS fuses Fibonacci time lattices, Lighthouse consensus, and autonomous execution to deliver institution-grade performance in a single platform.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <button
                onClick={onStartTrading}
                className="inline-flex items-center justify-center gap-3 rounded-full bg-gradient-to-r from-orange-400 via-fuchsia-500 to-purple-600 px-8 py-3 text-base font-semibold text-white shadow-xl shadow-fuchsia-500/40 transition hover:scale-[1.02]"
              >
                Start Trading Now
                <span aria-hidden className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/20 text-lg">
                  →
                </span>
              </button>
              <a
                className="inline-flex items-center justify-center gap-3 rounded-full border border-purple-400/50 bg-white/5 px-8 py-3 text-base font-semibold text-slate-200 backdrop-blur transition hover:bg-white/10"
                href="#features"
              >
                Watch Demo
              </a>
            </div>
            <div className="mt-12 grid w-full gap-6 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur md:grid-cols-3">
              {metrics.map((metric) => (
                <div key={metric.label} className="flex flex-col items-center justify-center gap-2">
                  <span className="text-3xl font-bold text-white md:text-4xl">{metric.value}</span>
                  <span className="text-xs uppercase tracking-[0.4em] text-slate-400">{metric.label}</span>
                </div>
              ))}
            </div>
          </section>

          <section id="features" className="mx-auto max-w-6xl px-6 pb-24">
            <div className="flex flex-col gap-6 text-center md:flex-row md:items-end md:justify-between md:text-left">
              <div>
                <p className="text-sm uppercase tracking-[0.4em] text-purple-300">Cutting-Edge Features</p>
                <h2 className="mt-3 text-3xl font-semibold text-white md:text-4xl">Experience the future of trading today.</h2>
              </div>
              <p className="max-w-xl text-slate-300">
                Every module inside AQTS is meticulously crafted to translate the QGITA framework into decisive market action. From pattern detection to execution, the visuals keep complex intelligence intuitive.
              </p>
            </div>

            <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              {features.map((feature) => (
                <article
                  key={feature.title}
                  className={`group rounded-3xl border border-white/10 bg-gradient-to-br ${feature.gradient} p-6 shadow-lg shadow-black/30 transition hover:-translate-y-1 hover:border-white/20 hover:shadow-purple-500/20`}
                >
                  <div
                    className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${feature.iconGradient} text-lg shadow-lg shadow-black/40 transition group-hover:scale-110`}
                    aria-hidden
                  >
                    {feature.icon}
                  </div>
                  <h3 className="mt-6 text-xl font-semibold text-white">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">{feature.description}</p>
                </article>
              ))}
            </div>
          </section>

          <section id="technology" className="mx-auto max-w-6xl px-6 pb-24">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-10 backdrop-blur">
              <p className="text-sm uppercase tracking-[0.4em] text-purple-300">QGITA Technology Stack</p>
              <h2 className="mt-4 max-w-3xl text-3xl font-semibold text-white md:text-4xl">
                The Aureon console visualizes each layer of the quantum detection pipeline with clarity and purpose.
              </h2>
              <div className="mt-10 grid gap-10 md:grid-cols-3">
                {pillars.map((pillar) => (
                  <div key={pillar.title} className="flex flex-col gap-4">
                    <div className="inline-flex w-fit rounded-full border border-purple-400/40 bg-purple-500/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-purple-200">
                      {pillar.title}
                    </div>
                    <p className="text-sm text-slate-300">{pillar.description}</p>
                    <ul className="space-y-2 text-sm text-slate-400">
                      {pillar.points.map((point) => (
                        <li key={point} className="flex items-start gap-3">
                          <span className="mt-1 inline-flex h-2 w-2 rounded-full bg-purple-300" />
                          <span>{point}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section id="pricing" className="mx-auto max-w-6xl px-6 pb-24">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-10 backdrop-blur">
              <div className="flex flex-col gap-6 text-center md:flex-row md:items-center md:justify-between md:text-left">
                <div>
                  <p className="text-sm uppercase tracking-[0.4em] text-purple-300">Launch Ready</p>
                  <h2 className="mt-3 text-3xl font-semibold text-white md:text-4xl">
                    Deploy AQTS in hours, not weeks.
                  </h2>
                </div>
                <p className="max-w-xl text-slate-300">
                  Seamless onboarding, guided configuration, and a dedicated success engineer ensure you generate alpha from day one.
                </p>
              </div>

              <div className="mt-12 grid gap-6 md:grid-cols-2">
                <div className="flex h-full flex-col gap-6 rounded-3xl border border-purple-400/40 bg-gradient-to-br from-purple-700/30 via-indigo-800/20 to-slate-900/40 p-8">
                  <div>
                    <h3 className="text-xl font-semibold text-white">Professional Console</h3>
                    <p className="mt-2 text-sm text-slate-300">Full access to live analytics, automation controls, and the Aureon dashboard.</p>
                  </div>
                  <ul className="space-y-3 text-sm text-slate-200">
                    <li className="flex items-center gap-3">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-base text-purple-200">✓</span>
                      Advanced QGITA detection engine visualizations
                    </li>
                    <li className="flex items-center gap-3">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-base text-purple-200">✓</span>
                      Automated trade execution with granular controls
                    </li>
                    <li className="flex items-center gap-3">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-base text-purple-200">✓</span>
                      Portfolio health, alerts, and performance analytics
                    </li>
                  </ul>
                  <button
                    onClick={onStartTrading}
                    className="mt-auto inline-flex items-center justify-center rounded-full bg-gradient-to-r from-purple-400 via-fuchsia-500 to-amber-400 px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-500/40 transition hover:scale-[1.01]"
                  >
                    Start Free Trial
                  </button>
                </div>
                <div className="flex h-full flex-col gap-6 rounded-3xl border border-white/10 bg-slate-900/60 p-8">
                  <div>
                    <h3 className="text-xl font-semibold text-white">Enterprise Partnership</h3>
                    <p className="mt-2 text-sm text-slate-300">Tailored deployment with liquidity routing, compliance tooling, and collaborative research.</p>
                  </div>
                  <ul className="space-y-3 text-sm text-slate-200">
                    <li className="flex items-center gap-3">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-base text-slate-200">✓</span>
                      Dedicated success engineering & white-glove onboarding
                    </li>
                    <li className="flex items-center gap-3">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-base text-slate-200">✓</span>
                      Multi-exchange infrastructure & API extensions
                    </li>
                    <li className="flex items-center gap-3">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-base text-slate-200">✓</span>
                      Governance, compliance, and reporting automations
                    </li>
                  </ul>
                  <a
                    className="mt-auto inline-flex items-center justify-center rounded-full border border-white/20 bg-white/5 px-8 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                    href="mailto:hello@aureon.ai"
                  >
                    Talk to Sales
                  </a>
                </div>
              </div>
            </div>
          </section>

          <section id="support" className="mx-auto max-w-5xl px-6 pb-28 text-center">
            <h2 className="text-3xl font-semibold text-white md:text-4xl">Ready to build your quantum trading edge?</h2>
            <p className="mx-auto mt-4 max-w-3xl text-slate-300">
              Join elite traders, funds, and innovators leveraging the Aureon Quantum Trading System to fund their boldest visions. Activate AQTS today and move from signal discovery to automated profit capture with confidence.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <button
                onClick={onStartTrading}
                className="inline-flex items-center justify-center gap-3 rounded-full bg-gradient-to-r from-orange-400 via-pink-500 to-purple-600 px-8 py-3 text-base font-semibold text-white shadow-lg shadow-purple-500/40 transition hover:scale-[1.02]"
              >
                Launch the Console
              </button>
              <a
                className="inline-flex items-center justify-center gap-3 rounded-full border border-white/20 bg-white/5 px-8 py-3 text-base font-semibold text-white transition hover:bg-white/10"
                href="mailto:support@aureon.ai"
              >
                Contact Support
              </a>
            </div>
          </section>
        </main>

        <footer className="relative z-10 border-t border-white/10 bg-[#070a1a]/90 py-10 text-center text-sm text-slate-500">
          <p>© {new Date().getFullYear()} Aureon Quantum Technologies. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
};

export default LandingPage;
