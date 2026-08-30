/**
 * SiteFooter — the company/legal footer shown on every surface (public + operator).
 *
 * Carries the registered legal entity, company number, copyright and license, plus
 * links to the legal, evidence, and company surfaces. Keeps the whole product
 * attributable and legally grounded no matter which screen a visitor is on.
 */

import { Link } from "react-router-dom";
import { COMPANY } from "./companyFacts";

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background/80 px-4 py-6 text-xs text-muted-foreground">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <p className="font-medium text-foreground">
            {COMPANY.registeredName}
          </p>
          <p>
            Trading as {COMPANY.tradingName} · Company No.{" "}
            <span className="font-mono">{COMPANY.companyNumber}</span> ·{" "}
            {COMPANY.registrar}
          </p>
          <p>
            {COMPANY.copyright} · Licensed under {COMPANY.license}
          </p>
        </div>
        <nav className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <Link to="/" className="hover:text-foreground">Home</Link>
          <Link to="/evidence" className="hover:text-foreground">Evidence</Link>
          <Link to="/company" className="hover:text-foreground">Company</Link>
          <Link to="/legal" className="hover:text-foreground">Legal</Link>
          <a href={COMPANY.repository} target="_blank" rel="noreferrer" className="hover:text-foreground">
            Repository
          </a>
          <a href={COMPANY.website} target="_blank" rel="noreferrer" className="hover:text-foreground">
            {COMPANY.websiteLabel}
          </a>
        </nav>
      </div>
      <p className="mx-auto mt-4 max-w-6xl text-[11px] leading-relaxed text-muted-foreground/80">
        Aureon OS is research and operational software. Nothing here is financial advice or an
        offer of securities. Trading involves substantial risk to capital — see the{" "}
        <Link to="/legal#risk" className="underline hover:text-foreground">risk disclosure</Link>.
      </p>
    </footer>
  );
}
