import React from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  NavLink,
  Link,
  Outlet,
} from 'react-router-dom';

import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SeroProvider } from './contexts/SeroProvider';
import { LiveNexusDataProvider, useLiveNexusData } from './contexts/LiveNexusDataContext';

import HomePage from './pages/HomePage';
import LiveStreamsPage from './pages/LiveStreamsPage';
import AboutPage from './pages/AboutPage';
import ResourcesPage from './pages/ResourcesPage';
import SupportPage from './pages/SupportPage';
import ScrollsPage from './pages/ScrollsPage';
import RitualPage from './pages/RitualPage';
import TermsOfUsePage from './pages/TermsOfUsePage';
import LoginPage from './pages/LoginPage';

import type { RealtimeMetric } from './hooks/useResampledNexusData';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';

const navigation = [
  { label: 'Console', to: '/' },
  { label: 'Live Streams', to: '/live' },
  { label: 'Ritual', to: '/ritual' },
  { label: 'Scrolls', to: '/scrolls' },
  { label: 'Resources', to: '/resources' },
  { label: 'Support', to: '/support' },
];

type NavigationItem = (typeof navigation)[number];

const formatMetricValue = (metric: RealtimeMetric): string => {
  switch (metric.format) {
    case 'ratio':
      return `${Math.round(metric.value * 100)}%`;
    case 'percent':
      return `${Math.round(metric.value)}${metric.unit || '%'}`;
    case 'count':
      return metric.unit ? `${metric.value.toLocaleString()} ${metric.unit}` : metric.value.toLocaleString();
    default:
      return metric.value.toString();
  }
};

const formatMetricDelta = (metric: RealtimeMetric): string => {
  const delta = metric.change ?? 0;
  if (!delta) {
    return 'Stable';
  }

  const sign = delta > 0 ? '+' : '';

  switch (metric.format) {
    case 'ratio':
      return `${sign}${(delta * 100).toFixed(1)}%`;
    case 'percent':
      return `${sign}${delta.toFixed(1)}${metric.unit || '%'}`;
    case 'count':
      return `${sign}${delta.toFixed(0)}${metric.unit ? ` ${metric.unit}` : ''}`;
    default:
      return `${sign}${delta.toString()}`;
  }
};

const formatRelativeTime = (timestamp: number): string => {
  const diffSeconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (diffSeconds < 60) {
    return `${diffSeconds}s ago`;
  }
  const diffMinutes = Math.round(diffSeconds / 60);
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }
  const diffHours = Math.round(diffMinutes / 60);
  return `${diffHours}h ago`;
};

const MetricBadge: React.FC<{ metric: RealtimeMetric }> = ({ metric }) => {
  const deltaLabel = formatMetricDelta(metric);
  const deltaPositive = metric.change !== undefined && metric.change > 0;
  const deltaNegative = metric.change !== undefined && metric.change < 0;

  return (
    <div className="flex flex-col rounded-2xl border border-white/10 bg-white/5 px-4 py-3 shadow-[0_0_18px_rgba(56,189,248,0.2)]">
      <span className="text-[10px] font-semibold uppercase tracking-[0.36em] text-white/60">
        {metric.label}
      </span>
      <span className="mt-2 text-lg font-semibold tracking-[0.18em] text-white">
        {formatMetricValue(metric)}
      </span>
      <span
        className={`mt-1 text-[10px] uppercase tracking-[0.32em] ${
          deltaPositive
            ? 'text-emerald-300'
            : deltaNegative
              ? 'text-rose-300'
              : 'text-slate-300/70'
        }`}
      >
        {deltaLabel}
      </span>
    </div>
  );
};

const LiveStatusStrip: React.FC = () => {
  const { metrics, timestamp, quantumLink } = useLiveNexusData();

  const highlightMetrics = metrics.slice(0, 3);
  const attunementPercent = Math.round((quantumLink?.observerAttunement ?? 0) * 100);
  const handshakeState = quantumLink?.handshakeState ?? 'idle';

  const handshakeVariant: 'success' | 'info' | 'secondary' = handshakeState === 'entangled'
    ? 'success'
    : handshakeState === 'auto-dial'
      ? 'info'
      : 'secondary';

  return (
    <div className="flex flex-col gap-4 border-t border-white/5 bg-[rgba(10,15,40,0.85)] px-6 py-4">
      <div className="flex flex-wrap items-center gap-4">
        {highlightMetrics.map((metric) => (
          <MetricBadge key={metric.id} metric={metric} />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-4 text-[11px] uppercase tracking-[0.32em] text-slate-300/80">
        <Badge variant={handshakeVariant} className="px-3 py-1 text-[10px] uppercase tracking-[0.32em]">
          Quantum Link · {handshakeState.replace('-', ' ')} · {attunementPercent}%
        </Badge>
        {quantumLink?.entangledTemporalId && (
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-white/80">
            Temporal ID: {quantumLink.entangledTemporalId}
          </span>
        )}
        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-white/60">
          Updated {formatRelativeTime(timestamp)}
        </span>
      </div>
    </div>
  );
};

const NavigationLink: React.FC<NavigationItem> = ({ label, to }) => (
  <NavLink
    to={to}
    end={to === '/'}
    className={({ isActive }) =>
      `rounded-full border px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.36em] transition-colors ${
        isActive
          ? 'border-cyan-400/60 bg-cyan-500/20 text-cyan-100 shadow-[0_0_25px_rgba(56,189,248,0.35)]'
          : 'border-white/10 bg-white/5 text-white/70 hover:text-white'
      }`
    }
  >
    {label}
  </NavLink>
);

const AppShell: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen flex-col text-slate-100">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[rgba(6,12,32,0.85)] backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
            <Link to="/" className="flex items-center gap-3 text-left">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-400/60 bg-cyan-500/20 text-sm font-semibold tracking-[0.3em] text-cyan-100 shadow-[0_0_25px_rgba(56,189,248,0.45)]">
                NX
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.5em] text-cyan-200/80">Harmonia Nexus</p>
                <p className="text-[11px] uppercase tracking-[0.36em] text-white/70">Live Field Console</p>
              </div>
            </Link>
            <nav className="flex flex-wrap gap-2">
              {navigation.map((item) => (
                <NavigationLink key={item.to} {...item} />
              ))}
            </nav>
          </div>
          <div className="flex flex-col items-start gap-3 text-left sm:flex-row sm:items-center sm:gap-5 lg:text-right">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.36em] text-white/80">
                {user?.name ?? 'Guest Observer'}
              </p>
              <p className="text-[10px] uppercase tracking-[0.32em] text-white/50">
                {user?.placeOfBirth ?? 'Awaiting alignment'}
              </p>
            </div>
            <Button
              variant="ghost"
              className="border border-white/10 bg-white/5 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.32em] text-white/70 hover:border-cyan-400/60 hover:bg-cyan-500/20 hover:text-cyan-100"
              onClick={logout}
            >
              Sign Out
            </Button>
          </div>
        </div>
        <LiveStatusStrip />
      </header>
      <main className="flex-1">
        <div className="mx-auto w-full max-w-7xl px-6 py-10">
          <Outlet />
        </div>
      </main>
      <footer className="border-t border-white/10 bg-[rgba(4,8,24,0.9)]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-6 py-6 text-[10px] uppercase tracking-[0.32em] text-white/50 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Harmonia Nexus Stewardship</p>
          <div className="flex flex-wrap items-center gap-4">
            <Link to="/about" className="transition hover:text-white/80">
              About
            </Link>
            <Link to="/terms-of-use" className="transition hover:text-white/80">
              Terms of Use
            </Link>
            <Link to="/support" className="transition hover:text-white/80">
              Support
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

const ProtectedRoute: React.FC = () => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <SeroProvider>
        <LiveNexusDataProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<ProtectedRoute />}>
                <Route element={<AppShell />}>
                  <Route index element={<HomePage />} />
                  <Route path="live" element={<LiveStreamsPage />} />
                  <Route path="about" element={<AboutPage />} />
                  <Route path="resources" element={<ResourcesPage />} />
                  <Route path="support" element={<SupportPage />} />
                  <Route path="scrolls" element={<ScrollsPage />} />
                  <Route path="ritual" element={<RitualPage />} />
                  <Route path="terms-of-use" element={<TermsOfUsePage />} />
                </Route>
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Router>
        </LiveNexusDataProvider>
      </SeroProvider>
    </AuthProvider>
  );
};

export default App;
