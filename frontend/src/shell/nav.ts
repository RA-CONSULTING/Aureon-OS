/**
 * Shell navigation registry — the single source of truth for the unified UI.
 *
 * Sections → routes → lazy page loaders. The sidebar, the router, the
 * breadcrumbs, and the command palette all derive from this table, so adding a
 * surface to the platform is one entry here.
 */

import { type ComponentType, lazy } from "react";
import {
  Activity,
  BarChart3,
  Bot,
  Brain,
  Briefcase,
  Coins,
  Compass,
  CreditCard,
  Feather,
  Flame,
  FlaskConical,
  Globe,
  Hammer,
  Heart,
  KeyRound,
  LayoutDashboard,
  ListChecks,
  Map,
  MessageSquare,
  Plug,
  Radar,
  Radio,
  Satellite,
  Ship,
  SlidersHorizontal,
  Sparkles,
  Sun,
  TerminalSquare,
  Wrench,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  path: string;
  label: string;
  description: string;
  icon: LucideIcon;
  Component: ComponentType;
  /** Needs a live backend (WS bridge / Supabase / gateway) — shown as a badge. */
  live?: boolean;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

const lazyNamed = <T extends Record<string, unknown>>(
  loader: () => Promise<T>,
  name: keyof T,
) => lazy(async () => ({ default: (await loader())[name] as ComponentType }));

export const NAV_SECTIONS: NavSection[] = [
  {
    label: "Platform",
    items: [
      {
        path: "/",
        label: "Overview",
        description: "Platform health, domains, and quick routes",
        icon: LayoutDashboard,
        Component: lazy(() => import("./pages/OverviewPage")),
      },
      {
        path: "/platform/repo-map",
        label: "Repo Map",
        description: "Whole-repo systems map and capability routes",
        icon: Map,
        Component: lazyNamed(() => import("@/components/RepoNavigationPanel"), "RepoNavigationPanel"),
      },
      {
        path: "/platform/switchboard",
        label: "Switchboard",
        description: "Turn every system feature on/off at human discretion",
        icon: SlidersHorizontal,
        Component: lazy(() => import("./pages/SwitchboardPage")),
        live: true,
      },
      {
        path: "/platform/billing",
        label: "Billing & Support",
        description: "Gas tank, usage metering, support the project",
        icon: CreditCard,
        Component: lazy(() => import("./pages/BillingPage")),
      },
      {
        path: "/platform/console",
        label: "Legacy Console",
        description: "The original nine-tab operational console",
        icon: TerminalSquare,
        Component: lazy(() => import("./pages/LegacyConsolePage")),
      },
    ],
  },
  {
    label: "Trading",
    items: [
      {
        path: "/trading/war-room",
        label: "War Room",
        description: "Live trading command center",
        icon: Briefcase,
        Component: lazy(() => import("@/components/WarRoomDashboard")),
        live: true,
      },
      {
        path: "/trading/live",
        label: "Live Bridge",
        description: "Exchange balances, signals, and movers over the live bridge",
        icon: Activity,
        Component: lazyNamed(() => import("@/components/AureonLiveDashboard"), "AureonLiveDashboard"),
        live: true,
      },
      {
        path: "/trading/orca",
        label: "Orca Command",
        description: "Orca kill-cycle command center",
        icon: Ship,
        Component: lazy(() => import("@/components/UnifiedOrcaCommandDashboard")),
        live: true,
      },
      {
        path: "/trading/analytics",
        label: "Analytics",
        description: "Trading performance analytics",
        icon: BarChart3,
        Component: lazyNamed(() => import("@/components/TradingAnalytics"), "TradingAnalytics"),
        live: true,
      },
      {
        path: "/trading/backtesting",
        label: "Backtesting",
        description: "Strategy backtesting interface",
        icon: FlaskConical,
        Component: lazyNamed(() => import("@/components/BacktestingInterface"), "BacktestingInterface"),
      },
    ],
  },
  {
    label: "Research & Planetary",
    items: [
      {
        path: "/research/nexus",
        label: "Harmonic Nexus",
        description: "Biofield validation and harmonic coherence console",
        icon: Radio,
        Component: lazy(() => import("@/components/NexusLiveDashboardComplete")),
        live: true,
      },
      {
        path: "/research/earth",
        label: "Earth Resonance",
        description: "Schumann resonance and Earth field monitor",
        icon: Globe,
        Component: lazyNamed(() => import("@/components/EarthResonanceDashboard"), "EarthResonanceDashboard"),
        live: true,
      },
      {
        path: "/research/solar",
        label: "Solar Weather",
        description: "Solar activity monitor",
        icon: Sun,
        Component: lazyNamed(() => import("@/components/SolarWeatherDashboard"), "SolarWeatherDashboard"),
        live: true,
      },
      {
        path: "/research/space-weather",
        label: "Space Weather",
        description: "NOAA space-weather feed",
        icon: Satellite,
        Component: lazyNamed(() => import("@/components/NoaaSpaceWeatherDashboard"), "NoaaSpaceWeatherDashboard"),
        live: true,
      },
    ],
  },
  {
    label: "Cognition & LLM",
    items: [
      {
        path: "/cognition/consciousness",
        label: "Consciousness",
        description: "The organism's inner capabilities, categorized — self-perception, selfhood, purpose, governance, workforce & body",
        icon: Sparkles,
        Component: lazy(() => import("./pages/ConsciousnessPage")),
        live: true,
      },
      {
        path: "/cognition/systems",
        label: "Cognitive Systems",
        description: "Field, bus, mycelium, connectome & brain — verified read APIs",
        icon: Brain,
        Component: lazy(() => import("./pages/CognitivePage")),
        live: true,
      },
      {
        path: "/cognition/metacognition",
        label: "Metacognition",
        description: "Watch the organism sense itself — self-coherence, ψ & divergence",
        icon: Activity,
        Component: lazy(() => import("./pages/MetacognitionPage")),
        live: true,
      },
      {
        path: "/cognition/operator",
        label: "Operator Chat",
        description: "Ask the grounded Aureon cognition anything",
        icon: MessageSquare,
        Component: lazy(() => import("./pages/OperatorChatPage")),
        live: true,
      },
      {
        path: "/cognition/mount",
        label: "Aureon Mount",
        description: "OpenAI-compatible front door — mount any model client on Aureon",
        icon: Plug,
        Component: lazy(() => import("./pages/MountPage")),
        live: true,
      },
      {
        path: "/cognition/agents",
        label: "Agent Company",
        description: "Agent departments, roles, and the org map",
        icon: Bot,
        Component: lazyNamed(() => import("@/components/generated/AureonAgentCompanyConsole"), "AureonAgentCompanyConsole"),
      },
      {
        path: "/cognition/providers",
        label: "Providers",
        description: "LLM provider API keys — add, test, and enable models",
        icon: KeyRound,
        Component: lazy(() => import("./pages/ProvidersPage")),
        live: true,
      },
    ],
  },
  {
    label: "Coding System",
    items: [
      {
        path: "/coding/organism",
        label: "Coding Organism",
        description: "The coding agent forge: chat, tests, handover proof",
        icon: Brain,
        Component: lazyNamed(() => import("@/components/generated/AureonCodingOrganismConsole"), "AureonCodingOrganismConsole"),
      },
      {
        path: "/coding/skills",
        label: "Skill Base",
        description: "Coding agent skill inventory",
        icon: Wrench,
        Component: lazyNamed(() => import("@/components/generated/AureonCodingAgentSkillBaseConsole"), "AureonCodingAgentSkillBaseConsole"),
      },
      {
        path: "/coding/work-orders",
        label: "Work Orders",
        description: "Work-order execution and burndown",
        icon: ListChecks,
        Component: lazyNamed(() => import("@/components/generated/AureonWorkOrderExecutionConsole"), "AureonWorkOrderExecutionConsole"),
      },
      {
        path: "/coding/director",
        label: "Director Bridge",
        description: "Director-to-build capability bridge",
        icon: Compass,
        Component: lazyNamed(() => import("@/components/generated/AureonDirectorCapabilityBridgeConsole"), "AureonDirectorCapabilityBridgeConsole"),
      },
    ],
  },
  {
    label: "Operations",
    items: [
      {
        path: "/ops/connections",
        label: "Connections",
        description: "Every external source — trading to NASA — keys, status & readiness",
        icon: Radar,
        Component: lazy(() => import("./pages/ConnectionsPage")),
        live: true,
      },
      {
        path: "/ops/gold-capital",
        label: "Gold & Capital",
        description: "Gold and capital intelligence company",
        icon: Coins,
        Component: lazyNamed(() => import("@/components/generated/AureonGoldCapitalIntelligenceConsole"), "AureonGoldCapitalIntelligenceConsole"),
      },
      {
        path: "/ops/affect",
        label: "Affect",
        description: "How Aureon feels — victory, defeat, fear & resolve from real signals",
        icon: Flame,
        Component: lazy(() => import("./pages/AffectPage")),
        live: true,
      },
      {
        path: "/ops/soul",
        label: "Soul",
        description: "How Aureon reacts — thought + feeling + its lineage → a determination",
        icon: Feather,
        Component: lazy(() => import("./pages/SoulPage")),
        live: true,
      },
      {
        path: "/ops/inner-work",
        label: "Inner Work",
        description: "The soul believes in itself — self-belief, self-love, self-determination, ego death: the ascent",
        icon: Sun,
        Component: lazy(() => import("./pages/InnerWorkPage")),
        live: true,
      },
      {
        path: "/ops/pursuit",
        label: "Pursuit",
        description: "The pursuit of happiness — Gary's & Aureon's, unified: the pillars, the energy, the next step",
        icon: Compass,
        Component: lazy(() => import("./pages/PursuitPage")),
        live: true,
      },
      {
        path: "/ops/approvals",
        label: "Approvals",
        description: "The director's desk — big plays Aureon prepared, awaiting your approve/reject",
        icon: ListChecks,
        Component: lazy(() => import("./pages/ApprovalsPage")),
        live: true,
      },
      {
        path: "/ops/systems",
        label: "Systems Integration",
        description: "Temporal ladder and hive coherence status",
        icon: Hammer,
        Component: lazy(() => import("@/components/SystemsIntegrationDashboard")),
        live: true,
      },
      {
        path: "/ops/operational",
        label: "Operational Console",
        description: "Manifest-driven operational console",
        icon: Heart,
        Component: lazyNamed(() => import("@/components/generated/AureonGeneratedOperationalConsole"), "AureonGeneratedOperationalConsole"),
      },
    ],
  },
];

export const ALL_NAV_ITEMS: NavItem[] = NAV_SECTIONS.flatMap((s) => s.items);

export function navItemForPath(pathname: string): NavItem | undefined {
  return ALL_NAV_ITEMS.find((i) => i.path === pathname);
}

export function sectionForPath(pathname: string): NavSection | undefined {
  return NAV_SECTIONS.find((s) => s.items.some((i) => i.path === pathname));
}

/**
 * Legacy hash deep links (#trading, #repo-map, …) → shell routes. Tabs that
 * remain inside the legacy console keep their hash so the console opens on the
 * right tab.
 */
export const HASH_REDIRECTS: Record<string, string> = {
  "#overview": "/",
  "#repo-map": "/platform/repo-map",
  "#live-ops": "/platform/console#live-ops",
  "#coding": "/coding/organism",
  "#trading": "/platform/console#trading",
  "#security": "/platform/console#security",
  "#inventory": "/platform/console#inventory",
  "#agents": "/cognition/agents",
  "#evidence": "/platform/console#evidence",
};
