import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Info, FileText, Shield } from "lucide-react";
import { LEGAL_EFFECTIVE_DATE } from "@/shell/companyFacts";

export function SettingsDrawer() {
  const [open, setOpen] = useState(false);
  // Honest backend status: probe the gateway health endpoint instead of asserting
  // a hardcoded "connected". undefined = checking, true = reachable, false = offline.
  const [backendUp, setBackendUp] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    setBackendUp(undefined);
    fetch("/healthz")
      .then((r) => alive && setBackendUp(r.ok))
      .catch(() => alive && setBackendUp(false));
    return () => {
      alive = false;
    };
  }, [open]);

  const feed =
    backendUp === undefined
      ? { dot: "bg-muted-foreground/50", cls: "text-muted-foreground", label: "Checking backend…" }
      : backendUp
        ? { dot: "bg-success animate-pulse", cls: "text-success", label: "Backend connected" }
        : { dot: "bg-muted-foreground/50", cls: "text-muted-foreground", label: "Backend not connected" };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon">
          <Info className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>About Aureon OS</SheetTitle>
          <SheetDescription>
            Aureon OS — Harmonic Nexus Core, by R&A Consulting and Brokerage Services Ltd
            (trading as Aureon Zorza Technologies)
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* System Info */}
          <div className="p-4 rounded-lg bg-muted/50 space-y-2">
            <h3 className="font-medium text-foreground">Backend status</h3>
            <p className="text-sm text-muted-foreground">
              Dashboards stream from the running Aureon backend (gateway / bridge / Supabase feed).
              With no backend connected, views render with empty or stale data — that is honest, not broken.
            </p>
            <div className="flex items-center gap-2 mt-3">
              <span className={`h-2 w-2 rounded-full ${feed.dot}`} />
              <span className={`text-xs font-medium ${feed.cls}`}>{feed.label}</span>
            </div>
          </div>

          <Accordion type="single" collapsible className="w-full">
            {/* Terms of Service */}
            <AccordionItem value="terms">
              <AccordionTrigger className="text-sm">
                <span className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Terms of Service
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <div className="text-sm text-muted-foreground space-y-4 py-2 max-h-[300px] overflow-y-auto">
                  <p className="text-xs">Last updated: {LEGAL_EFFECTIVE_DATE}</p>
                  
                  <div>
                    <h4 className="font-medium text-foreground mb-1">1. Acceptance of Terms</h4>
                    <p>By accessing and using Aureon OS, you agree to be bound by these Terms of Service.</p>
                  </div>

                  <div>
                    <h4 className="font-medium text-foreground mb-1">2. Description of Service</h4>
                    <p>Aureon OS is a grounded AI operating layer for evidence-heavy, high-control workflows. Sensitive actions (live trading, payments, filings) require explicit human approval — the platform never initiates them autonomously.</p>
                  </div>

                  <div>
                    <h4 className="font-medium text-foreground mb-1">3. Risk Disclosure</h4>
                    <p><strong className="text-destructive">IMPORTANT:</strong> Trading cryptocurrencies involves substantial risk of loss. You could lose some or all of your investment.</p>
                  </div>

                  <div>
                    <h4 className="font-medium text-foreground mb-1">4. Information Only</h4>
                    <p>This live feed is for informational purposes only. It displays the trading activity of the AUREON system but does not constitute financial advice.</p>
                  </div>

                  <div>
                    <h4 className="font-medium text-foreground mb-1">5. No Financial Advice</h4>
                    <p>The Service does not provide financial, investment, or trading advice. You are solely responsible for your own trading decisions.</p>
                  </div>

                  <div>
                    <h4 className="font-medium text-foreground mb-1">6. Limitation of Liability</h4>
                    <p>AUREON shall not be liable for any trading losses, system downtime, or any other damages arising from use of the Service.</p>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Privacy Policy */}
            <AccordionItem value="privacy">
              <AccordionTrigger className="text-sm">
                <span className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Privacy Policy
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <div className="text-sm text-muted-foreground space-y-4 py-2 max-h-[300px] overflow-y-auto">
                  <p className="text-xs">Last updated: {LEGAL_EFFECTIVE_DATE}</p>
                  
                  <div>
                    <h4 className="font-medium text-foreground mb-1">1. Information We Collect</h4>
                    <p>This is a public live feed. We do not collect any personal information from viewers.</p>
                  </div>

                  <div>
                    <h4 className="font-medium text-foreground mb-1">2. How We Protect Data</h4>
                    <ul className="list-disc list-inside space-y-1">
                      <li>TLS 1.3 for all data in transit</li>
                      <li>No personal data collection from viewers</li>
                      <li>Trading data displayed is from the system operator only</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-medium text-foreground mb-1">3. Data Sharing</h4>
                    <p>We do NOT share, sell, or rent any viewer data to third parties.</p>
                  </div>

                  <div>
                    <h4 className="font-medium text-foreground mb-1">4. Cookies</h4>
                    <p>This site may use minimal cookies for theme preferences only. No tracking cookies are used.</p>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          {/* Footer */}
          <div className="pt-4 border-t border-border text-center">
            <p className="text-xs text-muted-foreground">
              Aureon OS · Harmonic Nexus Core
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              © {new Date().getFullYear()} R&A Consulting and Brokerage Services Ltd · MIT License
            </p>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}