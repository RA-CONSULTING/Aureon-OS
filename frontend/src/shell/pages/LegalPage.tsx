/**
 * LegalPage — public /legal, with #terms #privacy #risk #disclaimer anchors.
 *
 * A UK/Northern Ireland baseline: Terms of Service, Privacy Policy (UK-GDPR),
 * Risk Disclosure, and general Disclaimer, all attributed to the registered company
 * with a fixed effective date. Backend-independent. These are templates pending
 * professional legal review — stated plainly at the top — not lawyer-drafted final copy.
 */

import { Link } from "react-router-dom";
import { FileText, Shield, AlertTriangle, ScrollText, Info } from "lucide-react";
import { COMPANY, LEGAL_EFFECTIVE_DATE } from "../companyFacts";

function Section({
  id,
  icon: Icon,
  title,
  children,
}: {
  id: string;
  icon: typeof FileText;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-border/60 pt-8">
      <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
        <Icon className="h-5 w-5 text-primary" />
        {title}
      </h2>
      <div className="mt-4 space-y-4 text-sm leading-relaxed text-muted-foreground">{children}</div>
    </section>
  );
}

function Clause({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="font-medium text-foreground">{heading}</h3>
      <p className="mt-1">{children}</p>
    </div>
  );
}

export default function LegalPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Legal &amp; Compliance</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {COMPANY.registeredName} (trading as {COMPANY.tradingName}) · Company No.{" "}
          <span className="font-mono">{COMPANY.companyNumber}</span> · {COMPANY.registrar}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">Effective date: {LEGAL_EFFECTIVE_DATE}</p>
        <div className="mt-4 flex items-start gap-2 rounded-md border border-primary/30 bg-primary/[0.04] px-3 py-2 text-xs text-muted-foreground">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <span>
            These policies are provided as templates pending review by qualified legal counsel for
            the relevant jurisdictions. They describe current intent in good faith and are not a
            substitute for professional legal advice.
          </span>
        </div>
        <nav className="mt-6 flex flex-wrap gap-x-4 gap-y-1 text-sm">
          <a href="#terms" className="text-primary hover:underline">Terms of Service</a>
          <a href="#privacy" className="text-primary hover:underline">Privacy Policy</a>
          <a href="#risk" className="text-primary hover:underline">Risk Disclosure</a>
          <a href="#disclaimer" className="text-primary hover:underline">Disclaimer</a>
        </nav>
      </header>

      <div className="mt-8 space-y-8">
        <Section id="terms" icon={FileText} title="Terms of Service">
          <Clause heading="1. Acceptance">
            By accessing or using Aureon OS (the “Service”), you agree to these Terms. If you do not
            agree, do not use the Service.
          </Clause>
          <Clause heading="2. The Service">
            Aureon OS is a grounded AI operating layer for evidence-heavy, high-control work. Sensitive
            actions — live trading, payments, external filings — require explicit human approval; the
            platform never initiates them autonomously.
          </Clause>
          <Clause heading="3. No financial advice">
            The Service is for research and informational purposes only. It does not constitute
            financial, investment, legal, or tax advice, and {COMPANY.registeredName} is not acting as
            an authorised or regulated financial adviser. You are solely responsible for your own
            decisions. See the <a href="#risk" className="text-primary hover:underline">Risk Disclosure</a>.
          </Clause>
          <Clause heading="4. Your responsibilities">
            You are responsible for the security of your own accounts and API credentials, for
            compliance with the laws and exchange terms applicable to you, and for any actions you
            approve through the Service.
          </Clause>
          <Clause heading="5. Limitation of liability">
            To the maximum extent permitted by law, {COMPANY.registeredName} shall not be liable for
            trading losses, lost profits, data loss, downtime, or any indirect or consequential damages
            arising from use of the Service. The software is provided “as is” under the {COMPANY.license}
            licence, without warranties of any kind.
          </Clause>
          <Clause heading="6. Governing law">
            These Terms are governed by the laws of Northern Ireland and the United Kingdom, and the
            courts of Northern Ireland have exclusive jurisdiction.
          </Clause>
        </Section>

        <Section id="privacy" icon={Shield} title="Privacy Policy">
          <Clause heading="1. Data controller">
            The data controller is {COMPANY.registeredName}, {COMPANY.registeredOffice}. Contact:{" "}
            <a href={`mailto:${COMPANY.email}`} className="text-primary hover:underline">{COMPANY.email}</a>.
          </Clause>
          <Clause heading="2. What we collect">
            Public informational surfaces do not collect personal data from visitors. When you operate
            your own instance and choose to connect exchanges or model providers, your own API
            credentials and configuration are stored encrypted at your instruction, to operate the
            Service on your behalf. We do not sell or rent personal data.
          </Clause>
          <Clause heading="3. How data is protected">
            Data in transit is encrypted (TLS). Secrets are held encrypted and are never committed to
            the repository. Access is limited to operating the Service you have configured.
          </Clause>
          <Clause heading="4. Your rights (UK GDPR)">
            Subject to applicable law you may request access to, correction of, or erasure of your
            personal data, and may object to or restrict certain processing. To exercise these rights,
            or to raise a complaint (including to the UK Information Commissioner’s Office), contact{" "}
            <a href={`mailto:${COMPANY.email}`} className="text-primary hover:underline">{COMPANY.email}</a>.
          </Clause>
          <Clause heading="5. Cookies">
            The Service uses minimal cookies/local storage for essential preferences (such as theme)
            and, where applicable, authenticated sessions. No third-party advertising trackers are used.
          </Clause>
        </Section>

        <Section id="risk" icon={AlertTriangle} title="Risk Disclosure">
          <div className="rounded-md border border-warning/40 bg-warning/10 p-3 text-warning">
            <strong>Trading involves substantial risk of loss and is not suitable for everyone.</strong>{" "}
            You may lose some or all of your capital. Only trade with money you can afford to lose.
          </div>
          <Clause heading="Not advice; not a regulated adviser">
            Nothing in the Service is a recommendation to buy, sell, or hold any asset.
            {" "}{COMPANY.registeredName} is not an authorised person under financial-services regulation
            and does not provide regulated investment advice or discretionary management.
          </Clause>
          <Clause heading="Past performance">
            Past or simulated performance is not indicative of future results. Backtests and research
            outputs are illustrative and may not reflect real trading conditions, fees, or slippage.
          </Clause>
          <Clause heading="Automation &amp; software risk">
            Automated systems can fail, misbehave under market extremes, or be affected by connectivity
            or software defects. Sensitive actions require your explicit approval; you remain
            responsible for monitoring and for the consequences of actions you authorise.
          </Clause>
        </Section>

        <Section id="disclaimer" icon={ScrollText} title="General Disclaimer">
          <p>
            Nothing on this site or in the Service is an offer of securities, a solicitation of
            investment, or a promise of returns. Company and recognition details (including Companies
            House registration {" "}
            <span className="font-mono">{COMPANY.companyNumber}</span> and the Innovate NI recognition)
            are stated as verifiable public facts. The research thesis is presented as pre-registered,
            falsifiable claims — see the{" "}
            <Link to="/evidence" className="text-primary hover:underline">Evidence</Link> page.
          </p>
        </Section>
      </div>
    </div>
  );
}
