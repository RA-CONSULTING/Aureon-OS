import { useState } from "react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Shield, Check, X, ExternalLink, AlertTriangle } from "lucide-react";

interface ExchangeGuide {
  name: string;
  color: string;
  url: string;
  permissions: { name: string; enabled: boolean; reason: string }[];
  steps: string[];
  warning: string;
}

const exchangeGuides: ExchangeGuide[] = [
  {
    name: "Binance",
    color: "text-warning",
    url: "https://www.binance.com/en/my/settings/api-management",
    permissions: [
      { name: "Enable Reading", enabled: true, reason: "Required to check balances" },
      { name: "Enable Spot & Margin Trading", enabled: true, reason: "Required to execute trades" },
      { name: "Enable Withdrawals", enabled: false, reason: "NEVER enable - we don't need withdrawal access" },
      { name: "Enable Futures", enabled: false, reason: "Not required for spot trading" },
    ],
    steps: [
      "Log in to Binance and go to API Management",
      "Click 'Create API' and complete 2FA verification",
      "Name your API key (e.g., 'AUREON Trading')",
      "Enable only 'Reading' and 'Spot & Margin Trading'",
      "Add IP whitelist for extra security (optional)",
      "Copy your API Key and Secret Key"
    ],
    warning: "Your Secret Key is only shown once. Save it securely!"
  },
  {
    name: "Kraken",
    color: "text-primary",
    url: "https://www.kraken.com/u/security/api",
    permissions: [
      { name: "Query Funds", enabled: true, reason: "Required to check balances" },
      { name: "Query Open Orders & Trades", enabled: true, reason: "Required to track positions" },
      { name: "Create & Modify Orders", enabled: true, reason: "Required to execute trades" },
      { name: "Cancel/Close Orders", enabled: true, reason: "Required for position management" },
      { name: "Withdraw Funds", enabled: false, reason: "NEVER enable - security risk" },
    ],
    steps: [
      "Log in to Kraken and go to Security → API",
      "Click 'Add Key'",
      "Set key description (e.g., 'AUREON')",
      "Select only trading-related permissions",
      "Complete 2FA verification",
      "Copy your API Key and Private Key"
    ],
    warning: "Private Key is only shown once during creation."
  },
  {
    name: "Alpaca",
    color: "text-success",
    url: "https://app.alpaca.markets/brokerage/dashboard/overview",
    permissions: [
      { name: "Trading", enabled: true, reason: "Required for stock trades" },
      { name: "Account", enabled: true, reason: "Required to check positions" },
    ],
    steps: [
      "Log in to Alpaca Dashboard",
      "Go to Paper Trading or Live Trading section",
      "Click 'View API Keys'",
      "Generate new API key pair",
      "Copy API Key ID and Secret Key"
    ],
    warning: "Start with Paper Trading to test before going live."
  },
  {
    name: "Capital.com",
    color: "text-primary",
    url: "https://capital.com/trading/platform",
    permissions: [
      { name: "API Access", enabled: true, reason: "Required for CFD trading" },
    ],
    steps: [
      "Log in to Capital.com",
      "Go to Settings → API",
      "Generate API credentials",
      "Note your account identifier (email)",
      "Copy API Key"
    ],
    warning: "CFD trading involves significant risk. Only trade what you can afford to lose."
  }
];

export function APIKeySecurityGuide() {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedExchange, setExpandedExchange] = useState<string | null>(null);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="border border-border/50 rounded-lg">
      <CollapsibleTrigger asChild>
        <Button variant="ghost" className="w-full justify-between p-3 h-auto">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">API Key Security Guide</span>
          </div>
          {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>
      </CollapsibleTrigger>
      
      <CollapsibleContent className="px-3 pb-3 space-y-3">
        <p className="text-xs text-muted-foreground">
          Follow these guides to create secure API keys for each exchange. 
          <strong className="text-destructive"> NEVER enable withdrawal permissions.</strong>
        </p>

        {exchangeGuides.map((guide) => (
          <Collapsible 
            key={guide.name}
            open={expandedExchange === guide.name}
            onOpenChange={(open) => setExpandedExchange(open ? guide.name : null)}
          >
            <CollapsibleTrigger asChild>
              <Button variant="outline" size="sm" className="w-full justify-between h-8">
                <span className={guide.color}>{guide.name}</span>
                {expandedExchange === guide.name ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </Button>
            </CollapsibleTrigger>
            
            <CollapsibleContent className="pt-2 space-y-3">
              {/* Permissions */}
              <div className="bg-muted/30 rounded p-2 space-y-1">
                <p className="text-xs font-medium mb-2">Required Permissions:</p>
                {guide.permissions.map((perm) => (
                  <div key={perm.name} className="flex items-start gap-2 text-xs">
                    {perm.enabled ? (
                      <Check className="h-3 w-3 text-success mt-0.5 shrink-0" />
                    ) : (
                      <X className="h-3 w-3 text-destructive mt-0.5 shrink-0" />
                    )}
                    <div>
                      <span className={perm.enabled ? "text-foreground" : "text-muted-foreground line-through"}>
                        {perm.name}
                      </span>
                      <span className="text-muted-foreground ml-1">— {perm.reason}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Steps */}
              <div className="space-y-1">
                <p className="text-xs font-medium">Setup Steps:</p>
                <ol className="list-decimal list-inside text-xs text-muted-foreground space-y-0.5">
                  {guide.steps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>

              {/* Warning */}
              <div className="flex items-start gap-2 text-xs text-warning bg-warning/10 rounded p-2">
                <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                <span>{guide.warning}</span>
              </div>

              {/* Link */}
              <a 
                href={guide.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                Open {guide.name} API Settings <ExternalLink className="h-3 w-3" />
              </a>
            </CollapsibleContent>
          </Collapsible>
        ))}
      </CollapsibleContent>
    </Collapsible>
  );
}
