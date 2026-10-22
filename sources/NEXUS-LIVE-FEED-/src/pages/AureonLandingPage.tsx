import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  BarChart3,
  BellRing,
  BookOpen,
  BrainCircuit,
  ChartCandlestick,
  CheckCircle2,
  Clock,
  Download,
  Fingerprint,
  Globe2,
  Layers,
  Lightbulb,
  Lock,
  LucideIcon,
  PlayCircle,
  Radar,
  Rocket,
  ShieldCheck,
  Sparkles,
  TimerReset,
  TrendingUp,
  Waves,
} from 'lucide-react';
import { Link } from 'react-router-dom';

const tickerPairs = [
  { pair: 'BTC/USDT', base: 67450, change: 2.3 },
  { pair: 'ETH/USDT', base: 3210, change: 1.8 },
  { pair: 'SOL/USDT', base: 182.5, change: -0.6 },
];

const featureList = [
  {
    title: 'Autonomous Trading',
    description: 'Deploy an always-on execution engine that hunts opportunity around the clock.',
    bullets: [
      "Hands-free automation tuned to Aureon's signal cadence",
      'Smart execution keeps slippage low and entries precise',
      '24/7 surveillance so you never miss a structural shift',
    ],
    icon: Rocket,
  },
  {
    title: 'Multi-Exchange Support',
    description: 'Seamlessly connect leading venues and command them from a unified console.',
    bullets: [
      'Trade Binance, Coinbase Pro, and Kraken in one view',
      'Cross-exchange arbitrage logic watches for mispricings',
      'Secure API vault with granular permissioning',
    ],
    icon: Globe2,
  },
  {
    title: 'Advanced Risk Management',
    description: 'Institutional-grade guardrails that defend capital while signals execute.',
    bullets: [
      'Dynamic position sizing anchored to live volatility',
      'Pre-programmed stop-loss, take-profit, and trail logic',
      'Daily loss caps and circuit breakers keep emotions out',
    ],
    icon: ShieldCheck,
  },
  {
    title: 'Real-Time Alerts',
    description: 'Stay in the loop from anywhere with multi-channel notifications.',
    bullets: [
      'Push, SMS, and email delivery within milliseconds',
      'Signal strength scoring clarifies conviction',
      'Entry and exit guidance for discretionary overlays',
    ],
    icon: BellRing,
  },
  {
    title: 'Backtesting & Analytics',
    description: 'Validate the edge with forensic-grade analytics before you deploy capital.',
    bullets: [
      'Replay years of market structure in minutes',
      'Sharpe, win rate, and drawdown dashboards',
      'One-click experiment sharing with teammates',
    ],
    icon: BarChart3,
  },
  {
    title: 'Paper Trading Mode',
    description: 'Master the workflow in a zero-risk environment backed by real market data.',
    bullets: [
      'Mirror live feeds with simulated balances',
      'Ideal for onboarding teams or refining strategies',
      'Graduate to live capital with confidence',
    ],
    icon: GraduationCap,
  },
] as const;

const differentiators = [
  {
    title: '99%+ reduction in false positives',
    description: 'Dual-stage validation filters out noise, leaving only mathematically verified shifts.',
  },
  {
    title: '5–15 minute early detection window',
    description: 'Curvature spikes surface before standard indicators, giving decisive lead time.',
  },
  {
    title: 'Peer-reviewed mathematical framework',
    description: 'Anchored in the Quantum Gravity in the Act (QGITA) research corpus.',
  },
  {
    title: 'Emotion-free execution',
    description: 'Sacred geometry and physics drive every decision—no guesswork required.',
  },
];

const pricingTiers = [
  {
    name: 'Free Trial',
    price: '£0',
    cadence: '7-day paper trading',
    description: 'Explore every feature without commitment.',
    features: ['All Aureon modules unlocked', 'Real market data with simulated trades', 'No credit card required'],
    cta: 'Start Free Trial',
    highlight: true,
  },
  {
    name: 'Starter',
    price: '£97',
    cadence: 'per month',
    description: 'Perfect for traders scaling their first system.',
    features: ['Up to £5,000 trading capital', '1 exchange connection', 'Guided analytics & email support'],
    cta: 'Start Trading',
  },
  {
    name: 'Professional',
    price: '£297',
    cadence: 'per month',
    description: 'Serious automation with deeper analytics.',
    features: [
      'Up to £50,000 trading capital',
      '3 exchange connections',
      'Advanced analytics, backtesting & priority support',
    ],
    cta: 'Go Pro',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    cadence: '',
    description: 'Tailored deployments for desks and institutions.',
    features: [
      'Unlimited capital and exchange coverage',
      'Dedicated quant team & white-label options',
      'API and custom algorithmic tuning',
    ],
    cta: 'Contact Sales',
  },
] as const;

const faqItems = [
  {
    question: 'Is this a scam or get-rich-quick scheme?',
    answer:
      'No. QGITA is a mathematical framework based on peer-reviewed research. Trading always carries risk and past performance never guarantees future outcomes. Aureon delivers tools and verified signals; you remain in control of your capital.',
  },
  {
    question: 'Do I need trading experience?',
    answer:
      'Experience helps, but it is not required. Guided onboarding, paper trading, and educational resources make it easy to learn at your own pace.',
  },
  {
    question: 'How much capital do I need?',
    answer:
      'We recommend starting with at least £500. Begin small, prove the edge with paper trading, then scale live capital as confidence grows.',
  },
  {
    question: 'Can I lose money?',
    answer:
      "Yes. All trading involves risk. Aureon's layered risk management reduces downside, but no system is infallible. Never invest more than you can afford to lose.",
  },
  {
    question: 'What exchanges are supported?',
    answer:
      'We currently support Binance, Coinbase Pro, and Kraken with more venues on the roadmap.',
  },
  {
    question: 'Is my API key safe?',
    answer:
      'Absolutely. We never request withdrawal permissions. You retain full custody while Aureon executes trades through encrypted API channels.',
  },
  {
    question: 'Can I cancel anytime?',
    answer:
      'Yes. There are no contracts. Cancel anytime with a single click inside the dashboard.',
  },
  {
    question: 'What is the historical win rate?',
    answer:
      "Aureon's historical win rate ranges between 75–85%, depending on market regime and risk configuration. Individual results may vary.",
  },
];

const metricsGrid = [
  { label: 'Signal Accuracy', traditional: '40–60%', aureon: '75–85%' },
  { label: 'False Positives', traditional: 'High (100s/day)', aureon: 'Ultra-low (1–3/day)' },
  { label: 'Emotional Trading', traditional: 'Yes', aureon: 'Eliminated' },
  { label: 'Time Required', traditional: 'Hours/day', aureon: 'Minutes/week' },
  { label: 'Learning Curve', traditional: 'Steep', aureon: 'Guided onboarding' },
  { label: 'Risk Management', traditional: 'Manual', aureon: 'Automated' },
];

const testimonials = [
  {
    quote: 'I went from losing £500/month to making £3,000+ consistently. QGITA changed everything.',
    name: 'James M.',
    location: 'London, UK',
  },
  {
    quote: 'Finally, a system that actually works. The Fibonacci detection is genius.',
    name: 'Sarah K.',
    location: 'Belfast, UK',
  },
  {
    quote: 'I run it alongside my day job. Passive income while I focus on my business.',
    name: 'David R.',
    location: 'Dublin, IE',
  },
];

const roadmapSteps = [
  {
    title: 'Sign Up',
    description: 'Create your account in under 30 seconds—no credit card required.',
    icon: Fingerprint,
    timing: '30 seconds',
  },
  {
    title: 'Connect Exchange',
    description: 'Securely plug in your API keys with guided videos and instant validation.',
    icon: Lock,
    timing: '2 minutes',
  },
  {
    title: 'Configure Strategy',
    description: 'Select your risk posture, pairs, and smart guardrails in a few guided clicks.',
    icon: Layers,
    timing: '5 minutes',
  },
  {
    title: 'Activate & Monitor',
    description: 'Launch paper trading or go live. Track everything from web or mobile.',
    icon: Radar,
    timing: 'Live',
  },
  {
    title: 'Optimize & Scale',
    description: 'Review analytics, fine tune parameters, and scale capital once you are ready.',
    icon: TrendingUp,
    timing: 'Ongoing',
  },
];

const technicalBadges = [
  { label: 'Innovate NI Silver', icon: Sparkles },
  { label: 'ICO Registration: ZB928588', icon: ShieldCheck },
  { label: 'GDPR & ISO Compliant', icon: Lock },
  { label: 'Secure API · No Withdrawal Access', icon: Fingerprint },
];

const supportingLinks = [
  {
    title: 'About Aureon',
    description: 'Meet Gary Leckey, explore the mission, and see the team bringing quantum trading to life.',
    href: '#about',
  },
  {
    title: 'How It Works',
    description: 'Dive deeper into the QGITA stages with video walkthroughs and case studies.',
    href: '#how-it-works',
  },
  {
    title: 'Resources & Blog',
    description: 'Master Fibonacci, advanced risk frameworks, and crypto psychology.',
    href: '#resources',
  },
  {
    title: 'Support Center',
    description: 'Video tutorials, API setup guides, and live chat when you need a human.',
    href: '#support',
  },
];

type FeatureItem = (typeof featureList)[number];

type IconProps = {
  className?: string;
};

const GraduationCap: LucideIcon = (props: IconProps) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={props.className}
  >
    <path d="M3 9l9-5 9 5-9 5-9-5z" />
    <path d="M21 14v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2" />
    <path d="M7 19.5a5 5 0 0 0 10 0" />
  </svg>
);

const AureonLandingPage: React.FC = () => {
  const [signalCount, setSignalCount] = useState(318);
  const [liveTicker, setLiveTicker] = useState(() =>
    tickerPairs.map((item) => ({
      ...item,
      price: item.base,
    })),
  );

  useEffect(() => {
    const signalInterval = window.setInterval(() => {
      setSignalCount((count) => count + Math.floor(Math.random() * 3));
    }, 4500);

    const tickerInterval = window.setInterval(() => {
      setLiveTicker((current) =>
        current.map((item) => {
          const drift = (Math.random() - 0.5) * (item.base * 0.0008);
          return {
            ...item,
            price: Math.max(item.base * 0.82, item.price + drift),
          };
        }),
      );
    }, 3200);

    return () => {
      window.clearInterval(signalInterval);
      window.clearInterval(tickerInterval);
    };
  }, []);

  const formattedTicker = useMemo(
    () =>
      liveTicker.map((item) => ({
        ...item,
        displayPrice: item.price.toLocaleString('en-GB', {
          minimumFractionDigits: item.price > 100 ? 0 : 2,
          maximumFractionDigits: item.price > 100 ? 0 : 2,
        }),
      })),
    [liveTicker],
  );

  return (
    <div className="min-h-screen bg-[#050815] text-slate-100">
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-32 left-1/2 h-[620px] w-[620px] -translate-x-1/2 rounded-full bg-gradient-to-br from-[#FFD700]/30 via-transparent to-transparent blur-[120px]" />
        <div className="absolute top-1/3 -left-40 h-[520px] w-[520px] rounded-full bg-gradient-to-br from-[#00ff88]/20 via-transparent to-transparent blur-[140px]" />
        <div className="absolute bottom-0 right-0 h-[460px] w-[460px] rounded-full bg-gradient-to-br from-[#4458ff]/20 via-transparent to-transparent blur-[160px]" />
      </div>

      <header className="relative border-b border-white/10 bg-[#070b1d]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-12 px-6 py-20 md:flex-row md:items-center md:gap-16 md:py-28">
          <div className="flex-1">
            <span className="inline-flex items-center rounded-full bg-white/10 px-4 py-1 text-sm uppercase tracking-[0.3em] text-[#FFD700]">
              Powered by the QGITA Framework
            </span>
            <h1 className="mt-6 max-w-2xl text-4xl font-bold leading-tight tracking-[0.08em] text-white sm:text-5xl lg:text-6xl">
              Trade Crypto Like Never Before: Quantum-Powered Precision
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-slate-200">
              QGITA technology detects hidden market events before they unfold. When sacred geometry meets algorithmic trading, you gain a measurable edge that is lightyears ahead of traditional indicators.
            </p>
            <p className="mt-3 text-base font-semibold uppercase tracking-[0.4em] text-[#FFD700]">
              Where Sacred Geometry Meets Algorithmic Trading
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                to="#pricing"
                className="group inline-flex items-center rounded-full bg-[#00ff88] px-6 py-3 text-base font-semibold text-[#04100b] transition hover:bg-[#00d976]"
              >
                Start Free Trial
                <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                to="#demo"
                className="inline-flex items-center rounded-full border border-[#FFD700]/60 px-6 py-3 text-base font-semibold text-[#FFD700] transition hover:bg-[#FFD700]/10"
              >
                <PlayCircle className="mr-2 h-5 w-5" />
                Watch Demo
              </Link>
              <div className="inline-flex items-center rounded-full border border-white/20 px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-300">
                No Credit Card Required
              </div>
            </div>

            <div className="mt-10 grid gap-5 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 via-white/5 to-white/0 p-5 shadow-lg shadow-black/20">
                <p className="text-sm uppercase tracking-[0.3em] text-slate-400">Trusted Network</p>
                <p className="mt-2 text-2xl font-semibold text-white">Join 500+ Traders Using Quantum Detection</p>
              </div>
              <div className="rounded-2xl border border-[#00ff88]/20 bg-[#00ff88]/5 p-5">
                <p className="text-sm uppercase tracking-[0.3em] text-[#00ff88]">Signals Detected Today</p>
                <p className="mt-2 text-3xl font-semibold text-white">{signalCount.toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-1 flex-col gap-6">
            <div className="rounded-3xl border border-white/10 bg-[#080e26]/80 p-6 shadow-2xl shadow-black/40">
              <div className="flex items-center justify-between text-xs uppercase tracking-[0.4em] text-slate-400">
                <span>Quantum Market Pulse</span>
                <span className="inline-flex items-center gap-1 text-[#00ff88]">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-[#00ff88]" /> Live
                </span>
              </div>
              <div className="mt-6 space-y-4">
                {formattedTicker.map((item) => (
                  <div key={item.pair} className="flex items-center justify-between rounded-2xl border border-white/5 bg-white/5 px-4 py-3">
                    <div className="flex items-center gap-3">
                      <ChartCandlestick className="h-5 w-5 text-[#FFD700]" />
                      <div>
                        <p className="text-sm font-semibold text-white">{item.pair}</p>
                        <p className={`text-xs ${item.change >= 0 ? 'text-[#00ff88]' : 'text-[#ff4444]'}`}>
                          {item.change >= 0 ? '+' : ''}
                          {item.change}% 24h
                        </p>
                      </div>
                    </div>
                    <p className="text-lg font-semibold text-white">{item.displayPrice}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-4 rounded-3xl border border-white/10 bg-[#070d24]/90 p-6 text-sm text-slate-200">
              <p className="flex items-center gap-2 text-[#FFD700]">
                <ShieldCheck className="h-5 w-5" /> Binance Compatible · Secure API · 24/7 Monitoring
              </p>
              <p className="flex items-center gap-2 text-[#00ff88]">
                <Radar className="h-5 w-5" /> Live Signal Indicator <span className="h-2 w-2 animate-pulse rounded-full bg-[#00ff88]" />
              </p>
              <p className="flex items-center gap-2">
                <TimerReset className="h-5 w-5 text-[#ff8e3c]" /> Detects events 5–15 minutes before traditional indicators
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="relative">
        <section id="problem" className="border-b border-white/10 bg-[#060a1b]/80 py-24">
          <div className="mx-auto grid max-w-6xl gap-12 px-6 lg:grid-cols-[1.3fr_1fr] lg:items-center">
            <div>
              <h2 className="text-3xl font-semibold tracking-[0.08em] text-white sm:text-4xl">Why 90% of Crypto Traders Lose Money</h2>
              <p className="mt-6 text-lg text-slate-200">
                Traditional playbooks rely on lagging indicators, emotional reactions, and scattered dashboards. Aureon cuts through the noise by revealing the hidden structure guiding price action.
              </p>
              <ul className="mt-8 space-y-4 text-slate-200">
                {[
                  'Emotion-driven entries and exits',
                  'False signals and relentless noise',
                  'Missed opportunities from slow reaction times',
                  'Over-trading burnout without a defined edge',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <span className="mt-1 h-2.5 w-2.5 rounded-full bg-[#ff4444]" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative rounded-3xl border border-[#ff4444]/30 bg-gradient-to-br from-[#17070f] via-[#230b1a] to-[#0d0618] p-8">
              <div className="absolute inset-x-8 -top-12 h-6 rounded-full bg-[#ff4444]/30 blur-xl" />
              <div className="space-y-5">
                <h3 className="text-2xl font-semibold text-[#ff7373]">Before Aureon</h3>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-5 text-sm text-slate-300">
                  <p>Chaotic charts. Late entries. Overwhelming alerts. Confidence erodes with every whipsaw.</p>
                </div>
                <h3 className="text-2xl font-semibold text-[#00ff88]">After Aureon</h3>
                <div className="rounded-2xl border border-[#00ff88]/30 bg-[#00ff88]/5 p-5 text-sm text-slate-100">
                  <p>Clean, geometry-verified signals surface ahead of the move. Execute decisively with quantified conviction.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="solution" className="border-b border-white/10 bg-[#070d24]/90 py-24">
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="text-3xl font-semibold tracking-[0.08em] text-white sm:text-4xl">Quantum Gravity in the Act: The Science Behind the Edge</h2>
              <p className="mt-6 text-lg text-slate-200">
                Aureon's two-stage detection system fuses sacred geometry with modern quant engineering, converting curvature anomalies into early trade signals.
              </p>
            </div>
            <div className="mt-16 grid gap-10 md:grid-cols-2">
              <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/10 via-white/5 to-transparent p-8">
                <div className="flex items-center gap-3 text-[#FFD700]">
                  <Waves className="h-6 w-6" />
                  <span className="text-xs uppercase tracking-[0.4em]">Stage 1</span>
                </div>
                <h3 className="mt-4 text-2xl font-semibold text-white">Fibonacci Time Lattice</h3>
                <p className="mt-4 text-slate-200">
                  Aureon scans live price data at golden-ratio intervals, identifying curvature spikes that mark structural shifts before price erupts.
                </p>
                <ul className="mt-6 space-y-3 text-sm text-slate-300">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="mt-1 h-4 w-4 text-[#00ff88]" />
                    <span>Automated lattice mapping across every integrated market pair.</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="mt-1 h-4 w-4 text-[#00ff88]" />
                    <span>Filters out noise to isolate geometry-backed inflection points.</span>
                  </li>
                </ul>
              </div>
              <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/10 via-white/5 to-transparent p-8">
                <div className="flex items-center gap-3 text-[#FFD700]">
                  <Lightbulb className="h-6 w-6" />
                  <span className="text-xs uppercase tracking-[0.4em]">Stage 2</span>
                </div>
                <h3 className="mt-4 text-2xl font-semibold text-white">Lighthouse Consensus</h3>
                <p className="mt-4 text-slate-200">
                  Five independent metrics validate each opportunity. Signals only trigger when every subsystem is in alignment, slashing false positives.
                </p>
                <ul className="mt-6 space-y-3 text-sm text-slate-300">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="mt-1 h-4 w-4 text-[#00ff88]" />
                    <span>Multi-layer confirmation spanning momentum, liquidity, and volatility.</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="mt-1 h-4 w-4 text-[#00ff88]" />
                    <span>Only verified signals propagate to execution, ensuring clarity.</span>
                  </li>
                </ul>
              </div>
            </div>
            <div className="mt-16 grid gap-6 md:grid-cols-2">
              {differentiators.map((item) => (
                <div key={item.title} className="rounded-2xl border border-white/10 bg-white/5 p-6">
                  <p className="text-base font-semibold text-white">{item.title}</p>
                  <p className="mt-3 text-sm text-slate-300">{item.description}</p>
                </div>
              ))}
            </div>
            <div className="mt-16 rounded-3xl border border-[#FFD700]/30 bg-gradient-to-br from-[#17192f] via-[#0c1328] to-[#060913] p-10">
              <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.4em] text-[#FFD700]">Signal Flow</p>
                  <h3 className="mt-3 text-2xl font-semibold text-white">From detection to execution in one seamless pipeline</h3>
                </div>
                <div className="flex flex-wrap items-center gap-4 text-sm text-slate-200">
                  {['Price Chart', 'FTCP Detection', 'Lighthouse Validation', 'Trade Signal'].map((stage, index) => (
                    <div key={stage} className="flex items-center gap-3">
                      {index > 0 && <ArrowRight className="h-4 w-4 text-[#FFD700]" />}
                      <span className="rounded-full border border-[#FFD700]/30 px-4 py-2 text-xs uppercase tracking-[0.3em] text-[#FFD700]">
                        {stage}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="border-b border-white/10 bg-[#050a1b] py-24">
          <div className="mx-auto max-w-6xl px-6">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-3xl font-semibold tracking-[0.08em] text-white sm:text-4xl">Features built for decisive trading</h2>
                <p className="mt-4 max-w-2xl text-lg text-slate-200">
                  Every module inside Aureon is engineered to translate quantum detection into confident execution. Explore the toolkit powering top-performing desks.
                </p>
              </div>
              <Link
                to="#demo"
                className="inline-flex items-center gap-2 rounded-full border border-white/20 px-5 py-2 text-sm font-semibold uppercase tracking-[0.3em] text-white transition hover:bg-white/10"
              >
                Explore the Demo
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="mt-12 grid gap-8 md:grid-cols-2">
              {featureList.map((feature) => (
                <FeatureCard key={feature.title} feature={feature} />
              ))}
            </div>

            <div className="mt-16 overflow-hidden rounded-3xl border border-white/10">
              <div className="grid gap-6 bg-gradient-to-br from-[#121937] via-[#0a1025] to-[#050815] p-8 lg:grid-cols-[0.8fr_1fr]">
                <div>
                  <p className="text-xs uppercase tracking-[0.4em] text-[#FFD700]">Compare the edge</p>
                  <h3 className="mt-3 text-2xl font-semibold text-white">Traditional trading vs. Aureon Quantum Trading</h3>
                  <p className="mt-4 text-sm text-slate-300">
                    The Aureon advantage is measurable. Here's how the numbers stack up against legacy tools and discretionary trading desks.
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full table-fixed text-left text-sm text-slate-200">
                    <thead className="text-xs uppercase tracking-[0.3em] text-slate-400">
                      <tr className="border-b border-white/10">
                        <th className="px-4 py-3">You Get</th>
                        <th className="px-4 py-3">Traditional Trading</th>
                        <th className="px-4 py-3">QGITA Aureon</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metricsGrid.map((row) => (
                        <tr key={row.label} className="border-b border-white/5 last:border-b-0">
                          <td className="px-4 py-3 font-semibold text-white">{row.label}</td>
                          <td className="px-4 py-3 text-slate-400">{row.traditional}</td>
                          <td className="px-4 py-3 text-[#00ff88]">{row.aureon}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="social-proof" className="border-b border-white/10 bg-[#070d24] py-24">
          <div className="mx-auto max-w-6xl px-6">
            <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-[#FFD700]">Performance</p>
                <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">Verified results trusted by 500+ traders</h2>
                <div className="mt-8 grid gap-6 sm:grid-cols-3">
                  {[
                    {
                      label: 'Verified Profits (90 days)',
                      value: '£127,000',
                    },
                    {
                      label: 'Average Win Rate',
                      value: '83%',
                    },
                    {
                      label: 'Average R:R',
                      value: '2.4 : 1',
                    },
                  ].map((stat) => (
                    <div key={stat.label} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{stat.label}</p>
                      <p className="mt-3 text-2xl font-semibold text-[#00ff88]">{stat.value}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-10 rounded-3xl border border-[#FFD700]/30 bg-[#171f3d]/60 p-8 text-sm text-slate-200">
                  <p className="font-semibold text-white">Live Performance Dashboard</p>
                  <p className="mt-3">
                    Monitor Aureon's performance in real time. Transparent daily updates, monthly reports, and soon-to-launch open-source validation keep you in the loop.
                  </p>
                </div>
              </div>
              <div className="space-y-6">
                {testimonials.map((item) => (
                  <blockquote key={item.name} className="rounded-3xl border border-white/10 bg-[#080f26]/80 p-8 text-slate-200 shadow-lg shadow-black/30">
                    <p className="text-lg text-white">“{item.quote}”</p>
                    <footer className="mt-4 text-sm text-slate-400">{item.name} · {item.location}</footer>
                  </blockquote>
                ))}
                <div className="grid gap-4 rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-slate-300">
                  {technicalBadges.map((badge) => (
                    <p key={badge.label} className="flex items-center gap-3 text-slate-200">
                      <badge.icon className="h-5 w-5 text-[#FFD700]" />
                      {badge.label}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-b border-white/10 bg-[#050a1b] py-24">
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-xs uppercase tracking-[0.4em] text-[#FFD700]">The Aureon Journey</p>
              <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">From setup to profit in under ten minutes</h2>
              <p className="mt-4 text-lg text-slate-200">
                Follow the guided path to deploy Aureon. Every step is streamlined with tutorials, live support, and automation.
              </p>
            </div>
            <div className="mt-14 grid gap-6 md:grid-cols-5">
              {roadmapSteps.map((step) => (
                <div key={step.title} className="relative flex flex-col items-center rounded-2xl border border-white/10 bg-white/5 p-5 text-center">
                  <step.icon className="h-8 w-8 text-[#FFD700]" />
                  <h3 className="mt-4 text-lg font-semibold text-white">{step.title}</h3>
                  <p className="mt-3 text-sm text-slate-300">{step.description}</p>
                  <span className="mt-4 text-xs uppercase tracking-[0.3em] text-[#00ff88]">{step.timing}</span>
                </div>
              ))}
            </div>
            <div className="mt-16 rounded-3xl border border-white/10 bg-[#07102a]/80 p-10">
              <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-[#FFD700]">User Experience</p>
                  <h3 className="mt-2 text-2xl font-semibold text-white">From signup to live trading in minutes</h3>
                  <p className="mt-3 max-w-xl text-sm text-slate-300">
                    Guided onboarding videos, interactive tooltips, and live chat keep you supported every step of the way. The Aureon mobile companion delivers signal alerts wherever you are.
                  </p>
                </div>
                <div className="flex flex-wrap gap-4 text-sm text-slate-200">
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/20 px-4 py-2">
                    <Download className="h-4 w-4" /> Mobile App Access
                  </span>
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/20 px-4 py-2">
                    <BookOpen className="h-4 w-4" /> Guided Onboarding
                  </span>
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/20 px-4 py-2">
                    <Clock className="h-4 w-4" /> 24/7 Priority Support
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="pricing" className="border-b border-white/10 bg-[#070d24] py-24">
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-xs uppercase tracking-[0.4em] text-[#FFD700]">Pricing & Packages</p>
              <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">Pick the Aureon plan that matches your ambition</h2>
              <p className="mt-4 text-lg text-slate-200">
                Start with a free trial or unlock pro capabilities. Every plan includes Aureon's quantum detection core, live support, and performance analytics.
              </p>
            </div>
            <div className="mt-12 grid gap-8 lg:grid-cols-4">
              {pricingTiers.map((tier) => (
                <div
                  key={tier.name}
                  className={`flex flex-col rounded-3xl border border-white/10 bg-[#080f26]/80 p-8 text-left shadow-xl shadow-black/30 ${
                    tier.highlight ? 'lg:-translate-y-6 lg:border-[#00ff88]/40 lg:bg-[#061f17]/90' : ''
                  }`}
                >
                  <div className="flex items-baseline justify-between">
                    <h3 className="text-2xl font-semibold text-white">{tier.name}</h3>
                    <span className="text-xs uppercase tracking-[0.3em] text-[#FFD700]">{tier.cadence}</span>
                  </div>
                  <p className="mt-6 text-3xl font-semibold text-[#00ff88]">{tier.price}</p>
                  <p className="mt-4 text-sm text-slate-300">{tier.description}</p>
                  <ul className="mt-6 space-y-3 text-sm text-slate-200">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-3">
                        <CheckCircle2 className="mt-1 h-4 w-4 text-[#00ff88]" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Link
                    to="#cta"
                    className={`mt-8 inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition ${
                      tier.highlight
                        ? 'bg-[#00ff88] text-[#04100b] hover:bg-[#00d976]'
                        : 'border border-white/20 text-white hover:bg-white/10'
                    }`}
                  >
                    {tier.cta}
                  </Link>
                </div>
              ))}
            </div>
            <div className="mt-12 flex flex-col gap-6 rounded-3xl border border-[#FFD700]/30 bg-[#171f3d]/60 p-10 text-sm text-slate-200 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-lg font-semibold text-white">30-Day Performance Guarantee</p>
                <p className="mt-2">If you don't see positive results in 30 days, we'll refund you—no questions asked.</p>
              </div>
              <div className="flex flex-wrap gap-4 text-xs uppercase tracking-[0.3em] text-slate-300">
                <span className="rounded-full border border-white/20 px-4 py-2">Credit & Debit Cards</span>
                <span className="rounded-full border border-white/20 px-4 py-2">Crypto: BTC · ETH · USDT</span>
                <span className="rounded-full border border-white/20 px-4 py-2">Annual Billing Save 20%</span>
              </div>
            </div>
          </div>
        </section>

        <section id="faq" className="border-b border-white/10 bg-[#050a1b] py-24">
          <div className="mx-auto max-w-5xl px-6">
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-xs uppercase tracking-[0.4em] text-[#FFD700]">Frequently Asked Questions</p>
              <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">Everything you need to know before you automate</h2>
            </div>
            <div className="mt-12 space-y-6">
              {faqItems.map((faq) => (
                <details
                  key={faq.question}
                  className="group rounded-3xl border border-white/10 bg-[#080f26]/80 p-6 text-left transition"
                >
                  <summary className="flex cursor-pointer items-center justify-between text-lg font-semibold text-white">
                    {faq.question}
                    <span className="ml-4 text-sm text-[#00ff88] group-open:text-[#FFD700]">Learn more</span>
                  </summary>
                  <p className="mt-4 text-sm text-slate-300">{faq.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section id="technical" className="border-b border-white/10 bg-[#070d24] py-24">
          <div className="mx-auto max-w-6xl px-6">
            <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-[#FFD700]">Technical Credibility</p>
                <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">Built on breakthrough research, not hype</h2>
                <p className="mt-5 text-lg text-slate-200">
                  Download the QGITA whitepaper, explore the published framework, and dive into the mathematics powering Aureon. Transparency is baked into every release.
                </p>
                <div className="mt-6 flex flex-wrap gap-4 text-sm text-slate-200">
                  <Link
                    to="/docs/qgita-whitepaper.pdf"
                    className="inline-flex items-center gap-2 rounded-full border border-white/20 px-5 py-2 transition hover:bg-white/10"
                  >
                    <Download className="h-4 w-4" /> QGITA Whitepaper
                  </Link>
                  <Link
                    to="#performance"
                    className="inline-flex items-center gap-2 rounded-full border border-white/20 px-5 py-2 transition hover:bg-white/10"
                  >
                    <BrainCircuit className="h-4 w-4" /> Research Highlights
                  </Link>
                </div>
                <div className="mt-10 grid gap-4 text-sm text-slate-300">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                    <p className="text-xs uppercase tracking-[0.3em] text-[#FFD700]">Leadership</p>
                    <p className="mt-2 text-white">Developed by R&A Consulting & Brokerage Services</p>
                    <p className="mt-1">Led by Gary Leckey—Quantum technology pioneer and Innovate NI Silver Award winner.</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
                    <p className="text-xs uppercase tracking-[0.3em] text-[#FFD700]">Transparency</p>
                    <p className="mt-2">Live performance dashboard, monthly reports, and open-source validation (coming soon).</p>
                  </div>
                </div>
              </div>
              <div className="space-y-6 rounded-3xl border border-white/10 bg-[#080f26]/80 p-8">
                <div className="rounded-2xl border border-[#FFD700]/30 bg-[#171f3d]/60 p-6 text-sm text-slate-200">
                  <p className="text-lg font-semibold text-white">ΔM = Ψ₀ × Ω × Λ × Φ × Σ</p>
                  <p className="mt-3">Core QGITA equation excerpt illustrating the quantum geometry transformations underlying Aureon's detection engine.</p>
                </div>
                <div className="grid gap-4 text-sm text-slate-200">
                  <p className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-[#FFD700]" /> Secure API Integration (No Withdrawal Access)
                  </p>
                  <p className="flex items-center gap-3">
                    <Sparkles className="h-5 w-5 text-[#FFD700]" /> Featured in Crypto Journal & Tech Innovation Award
                  </p>
                  <p className="flex items-center gap-3">
                    <Lock className="h-5 w-5 text-[#FFD700]" /> GDPR Compliant · ICO Registered (ZB928588)
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="cta" className="border-b border-white/10 bg-[#050a1b] py-24">
          <div className="mx-auto max-w-5xl px-6 text-center">
            <p className="text-xs uppercase tracking-[0.4em] text-[#FFD700]">Limited Beta Access</p>
            <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">Claim your free trial now—50 spots remaining this month</h2>
            <p className="mt-4 text-lg text-slate-200">
              Early adopters secure a lifetime 30% discount when the beta closes. Don't miss the chance to trade with quantum-grade foresight.
            </p>
            <div className="mt-10 flex flex-wrap justify-center gap-4">
              <Link
                to="#pricing"
                className="group inline-flex items-center gap-2 rounded-full bg-[#00ff88] px-8 py-3 text-base font-semibold text-[#04100b] transition hover:bg-[#00d976]"
              >
                Claim Your Free Trial Now
                <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                to="#resources"
                className="inline-flex items-center gap-2 rounded-full border border-white/20 px-8 py-3 text-base font-semibold text-white transition hover:bg-white/10"
              >
                Download the Free Guide
                <Download className="h-5 w-5" />
              </Link>
            </div>
            <p className="mt-6 text-sm text-slate-400">Join 500+ traders already profiting with QGITA.</p>
          </div>
        </section>

        <section id="resources" className="border-b border-white/10 bg-[#070d24] py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {supportingLinks.map((link) => (
                <Link
                  key={link.title}
                  to={link.href}
                  className="group rounded-3xl border border-white/10 bg-[#080f26]/80 p-6 transition hover:border-[#00ff88]/40 hover:bg-[#061f17]/80"
                >
                  <h3 className="text-lg font-semibold text-white">{link.title}</h3>
                  <p className="mt-3 text-sm text-slate-300">{link.description}</p>
                  <span className="mt-4 inline-flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-[#00ff88]">
                    Learn More <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-1" />
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-[#040716] py-16 text-sm text-slate-300">
        <div className="mx-auto grid max-w-6xl gap-10 px-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <h3 className="text-lg font-semibold text-white">Aureon Quantum Trading System</h3>
            <p className="mt-3 max-w-lg text-slate-400">
              R&A Consulting & Brokerage Services Ltd · Innovate NI Silver Award Winner. Trading involves risk. Past performance is not indicative of future results.
            </p>
            <div className="mt-6 flex flex-wrap gap-4 text-xs uppercase tracking-[0.3em] text-slate-400">
              <span>Binance Compatible</span>
              <span>Secure API</span>
              <span>24/7 Monitoring</span>
              <span>Quantum Verified</span>
            </div>
          </div>
          <div className="grid gap-8 sm:grid-cols-2">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Navigation</p>
              {['About Us', 'How It Works', 'Pricing', 'FAQ', 'Blog/Resources', 'Contact Support', 'Terms & Conditions', 'Privacy Policy', 'Risk Disclaimer'].map((item) => (
                <Link key={item} to={`/${item.toLowerCase().replace(/[^a-z]+/g, '-')}`} className="block text-slate-300 hover:text-white">
                  {item}
                </Link>
              ))}
            </div>
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Connect</p>
              <p>Email: <a href="mailto:support@aureontrading.com" className="text-white">support@aureontrading.com</a></p>
              <p>Phone: <a href="tel:+442033769641" className="text-white">+44 20 3376 9641</a></p>
              <p>Live Chat Available 24/7</p>
              <div className="mt-4 flex gap-3 text-slate-400">
                <Link to="https://twitter.com" className="hover:text-white">Twitter/X</Link>
                <Link to="https://linkedin.com" className="hover:text-white">LinkedIn</Link>
                <Link to="https://youtube.com" className="hover:text-white">YouTube</Link>
                <Link to="https://t.me" className="hover:text-white">Telegram</Link>
              </div>
              <p className="mt-6 text-xs uppercase tracking-[0.3em] text-slate-500">Legal</p>
              <p>R&A Consulting and Brokerage Services Ltd · NI696693</p>
              <p>ICO Registration: ZB928588</p>
            </div>
          </div>
        </div>
        <div className="mt-12 border-t border-white/10 pt-6 text-center text-xs text-slate-500">
          © {new Date().getFullYear()} Aureon Quantum Trading System. All rights reserved.
        </div>
      </footer>
    </div>
  );
};

const FeatureCard = ({ feature }: { feature: FeatureItem }) => (
  <div className="rounded-3xl border border-white/10 bg-[#080f26]/80 p-8 shadow-lg shadow-black/30 transition hover:border-[#00ff88]/40 hover:bg-[#061f17]/80">
    <feature.icon className="h-8 w-8 text-[#FFD700]" />
    <h3 className="mt-5 text-xl font-semibold text-white">{feature.title}</h3>
    <p className="mt-3 text-sm text-slate-300">{feature.description}</p>
    <ul className="mt-5 space-y-2 text-sm text-slate-200">
      {feature.bullets.map((bullet) => (
        <li key={bullet} className="flex items-start gap-2">
          <ArrowRight className="mt-1 h-3.5 w-3.5 text-[#00ff88]" />
          <span>{bullet}</span>
        </li>
      ))}
    </ul>
  </div>
);

export default AureonLandingPage;
