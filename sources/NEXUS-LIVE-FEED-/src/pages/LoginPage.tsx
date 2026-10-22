import React, { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, user } = useAuth();
  const [name, setName] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [placeOfBirth, setPlaceOfBirth] = useState('');
  const [error, setError] = useState('');

  const handleUseGaryProfile = () => {
    setName('Gary Leckey');
    setDateOfBirth('1991-11-02');
    setPlaceOfBirth('Belfast, Northern Ireland');
    setError('');
  };

  if (user) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !dateOfBirth || !placeOfBirth.trim()) {
      setError('All access credentials are required to synchronize with the bio-monitoring suite.');
      return;
    }

    setError('');
    login({ name: name.trim(), dateOfBirth, placeOfBirth: placeOfBirth.trim() });
    navigate('/', { replace: true });
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-slate-950 px-6 py-12 text-slate-100">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(56,189,248,0.15),_transparent_60%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.12),_transparent_70%)]" />
      <div className="relative z-10 w-full max-w-xl overflow-hidden rounded-3xl border border-slate-700/40 bg-slate-900/80 p-10 shadow-[0_0_40px_rgba(56,189,248,0.15)] backdrop-blur">
        <div className="mb-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.6em] text-cyan-300/80">Quantum Fit-Bit Access Ritual</p>
          <h1 className="mt-3 text-3xl font-semibold uppercase tracking-[0.35em] text-white">Human Connection Login</h1>
          <p className="mt-4 text-sm leading-relaxed text-slate-300/85">
            Authenticate with your origin coordinates to unlock the full suite of bio-monitoring systems and synchronize
            with the Harmonia Nexus live feed.
          </p>
          <div className="mt-5 flex flex-col items-center gap-2 text-[11px] uppercase tracking-[0.35em] text-slate-400">
            <span>Testing with Gary Leckey&apos;s timeline?</span>
            <button
              type="button"
              onClick={handleUseGaryProfile}
              className="rounded-full border border-cyan-400/50 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.35em] text-cyan-200 transition hover:border-cyan-300 hover:text-cyan-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/70"
            >
              Prefill Gary&apos;s Credentials
            </button>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="name" className="text-xs font-semibold uppercase tracking-[0.4em] text-slate-400">
              Name
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-700/50 bg-slate-950/80 px-4 py-3 text-sm text-white shadow-inner focus:border-cyan-400/70 focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
              placeholder="Enter your full name"
              autoComplete="name"
            />
          </div>
          <div>
            <label htmlFor="dateOfBirth" className="text-xs font-semibold uppercase tracking-[0.4em] text-slate-400">
              Date of Birth
            </label>
            <input
              id="dateOfBirth"
              type="date"
              value={dateOfBirth}
              onChange={(event) => setDateOfBirth(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-700/50 bg-slate-950/80 px-4 py-3 text-sm text-white shadow-inner focus:border-cyan-400/70 focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
              placeholder="Select your birth date"
            />
          </div>
          <div>
            <label htmlFor="placeOfBirth" className="text-xs font-semibold uppercase tracking-[0.4em] text-slate-400">
              Place of Birth
            </label>
            <input
              id="placeOfBirth"
              type="text"
              value={placeOfBirth}
              onChange={(event) => setPlaceOfBirth(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-700/50 bg-slate-950/80 px-4 py-3 text-sm text-white shadow-inner focus:border-cyan-400/70 focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
              placeholder="City, Country"
              autoComplete="off"
            />
          </div>
          {error && <p className="text-xs font-semibold uppercase tracking-[0.3em] text-rose-300">{error}</p>}
          <button
            type="submit"
            className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 via-blue-500 to-fuchsia-500 px-6 py-3 text-sm font-semibold uppercase tracking-[0.4em] text-white shadow-lg transition hover:shadow-[0_0_35px_rgba(56,189,248,0.35)] focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/70"
          >
            Initiate Synchronization
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
