import React from 'react';

const TermsOfUsePage: React.FC = () => (
  <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/80 p-8 text-slate-100 shadow-[0_0_45px_rgba(59,130,246,0.25)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.25),_transparent_60%)] opacity-80" />
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(79,70,229,0.18),_transparent_65%)] opacity-70" />
    <div className="relative z-10 space-y-6">
      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-emerald-300/90">Compliance Notice</p>
        <h1 className="text-3xl font-semibold uppercase tracking-[0.32em] text-white">SPOT Exchange Terms of Use</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-300/85">
          Binance products and services, including SPOT Exchange access, operate under the Binance Product Terms of Use. These
          terms outline your obligations, the safeguards in place to protect your account, and the conditions that govern
          every trade you execute on the platform. Please review the complete Product Terms before proceeding with any
          exchange activity.
        </p>
      </header>

      <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-6 text-sm leading-relaxed text-emerald-100">
        <h2 className="text-xs font-semibold uppercase tracking-[0.32em] text-emerald-200/90">
          Spot Testnet Terms of Use
        </h2>
        <p className="mt-3 text-emerald-100/90">
          The Binance Spot Testnet and Futures Testnet are each governed by the official{' '}
          <a
            className="text-emerald-200 underline decoration-emerald-400/70 underline-offset-4"
            href="https://www.binance.com/en/testnet/terms"
          >
            Testnet Terms of Use
          </a>
          . Please review these terms carefully before proceeding with any simulated trading activity.
        </p>
      </div>

      <div className="grid gap-5 rounded-2xl border border-white/10 bg-white/5 p-6 text-slate-200/90">
        <h2 className="text-sm font-semibold uppercase tracking-[0.28em] text-white/95">Key Points</h2>
        <ul className="space-y-3 text-sm leading-relaxed">
          <li>
            • Your continued use of SPOT Exchange services signifies agreement with the full Binance Product Terms of Use and any
            jurisdiction-specific addenda.
          </li>
          <li>
            • You are responsible for ensuring that trading activities comply with applicable laws and that you understand the
            risks of digital asset markets, including volatility and potential loss of capital.
          </li>
          <li>
            • Security requirements—such as maintaining account credentials, enabling two-factor authentication, and reporting
            suspicious activity—are mandatory to preserve market integrity.
          </li>
          <li>
            • Binance may modify its Product Terms of Use; it is your responsibility to stay informed about updates that could
            affect your rights or obligations.
          </li>
        </ul>
      </div>

      <footer className="space-y-3 text-sm leading-relaxed text-slate-300/85">
        <p>
          By selecting “Continue” in the SPOT Exchange console you acknowledge that you have read, understood, and agree to the
          Binance Product Terms of Use and any supplemental policies referenced therein.
        </p>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400/80">
          For the full legal text, visit <a className="text-emerald-300 underline decoration-emerald-500/60 decoration-dotted underline-offset-4" href="https://www.binance.com/en/terms">binance.com/en/terms</a>.
        </p>
      </footer>
    </div>
  </section>
);

export default TermsOfUsePage;
