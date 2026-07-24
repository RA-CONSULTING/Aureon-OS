/**
 * ShellLayout — the professional frame around every surface in the repo.
 *
 * Collapsible grouped sidebar (all platform surfaces from the nav registry),
 * top bar with breadcrumb, live platform-status indicator (GET /api/status),
 * command palette (Ctrl/Cmd-K) for jump-to-surface, and the routed page in a
 * per-route error boundary + suspense skeleton. Aureon prism identity, shadcn
 * primitives, zero new dependencies.
 */

import { Suspense, useCallback, useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { HASH_REDIRECTS, VISIBLE_NAV_SECTIONS, navItemForPath, sectionForPath } from "./nav";
import { PageSkeleton, RouteErrorBoundary } from "./Page";
import { BackendStatusBanner } from "@/components/BackendStatusBanner";
import { LiveVitals } from "@/components/LiveVitals";
import { SiteFooter } from "./SiteFooter";
import { RiskDisclaimer } from "@/components/RiskDisclaimer";
import { SupportProjectPrompt } from "@/components/SupportProjectPrompt";

type PlatformHealth = "healthy" | "degraded" | "critical" | "unknown";

function usePlatformStatus(): PlatformHealth {
  const [health, setHealth] = useState<PlatformHealth>("unknown");
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await fetch("/api/status", { cache: "no-store" });
        if (!r.ok) throw new Error(String(r.status));
        const j = (await r.json()) as { status?: string };
        if (!cancelled) {
          const s = String(j.status || "unknown");
          setHealth(s === "healthy" || s === "degraded" || s === "critical" ? (s as PlatformHealth) : "unknown");
        }
      } catch {
        if (!cancelled) setHealth("unknown");
      }
    };
    poll();
    const t = setInterval(poll, 30_000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);
  return health;
}

const STATUS_STYLE: Record<PlatformHealth, { dot: string; label: string }> = {
  healthy: { dot: "bg-success", label: "Healthy" },
  degraded: { dot: "bg-primary", label: "Degraded" },
  critical: { dot: "bg-destructive", label: "Critical" },
  unknown: { dot: "bg-muted-foreground", label: "No gateway" },
};

function StatusIndicator() {
  const health = usePlatformStatus();
  const s = STATUS_STYLE[health];
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground" title="Platform status (GET /api/status)">
      <span className={`h-2 w-2 rounded-full ${s.dot} ${health === "healthy" ? "animate-pulse" : ""}`} />
      {s.label}
    </div>
  );
}

function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const go = useCallback(
    (path: string) => {
      setOpen(false);
      navigate(path);
    },
    [navigate],
  );

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="h-8 gap-2 text-xs text-muted-foreground"
        onClick={() => setOpen(true)}
      >
        <Search className="h-3.5 w-3.5" />
        Jump to surface…
        <kbd className="pointer-events-none rounded border bg-muted px-1.5 font-mono text-[10px]">⌘K</kbd>
      </Button>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder="Search every surface in the platform…" />
        <CommandList>
          <CommandEmpty>No surface found.</CommandEmpty>
          {VISIBLE_NAV_SECTIONS.map((section) => (
            <CommandGroup key={section.label} heading={section.label}>
              {section.items.map((item) => (
                <CommandItem key={item.path} value={`${section.label} ${item.label}`} onSelect={() => go(item.path)}>
                  <item.icon className="mr-2 h-4 w-4" />
                  <span>{item.label}</span>
                  <span className="ml-2 truncate text-xs text-muted-foreground">{item.description}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          ))}
        </CommandList>
      </CommandDialog>
    </>
  );
}

function ShellSidebar() {
  const location = useLocation();
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <Link to="/" className="flex items-center gap-2 px-2 py-1.5">
          <BrandMark size={32} className="shrink-0" />
          <div className="grid leading-tight group-data-[collapsible=icon]:hidden">
            <span className="font-semibold tracking-wide">AUREON</span>
            <span className="text-[10px] text-muted-foreground">Harmonic Nexus Core</span>
          </div>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        {VISIBLE_NAV_SECTIONS.map((section) => (
          <SidebarGroup key={section.label}>
            <SidebarGroupLabel>{section.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items.map((item) => (
                  <SidebarMenuItem key={item.path}>
                    <SidebarMenuButton
                      asChild
                      isActive={location.pathname === item.path}
                      tooltip={item.label}
                    >
                      <Link to={item.path}>
                        <item.icon />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <div className="px-2 pb-2 group-data-[collapsible=icon]:hidden">
          <StatusIndicator />
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

function ShellBreadcrumb() {
  const location = useLocation();
  const item = navItemForPath(location.pathname);
  const section = sectionForPath(location.pathname);
  return (
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem className="hidden md:block">
          <BreadcrumbLink asChild>
            <Link to="/console">Aureon</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>
        {section && section.label !== "Platform" && (
          <>
            <BreadcrumbSeparator className="hidden md:block" />
            <BreadcrumbItem className="hidden md:block">{section.label}</BreadcrumbItem>
          </>
        )}
        <BreadcrumbSeparator className="hidden md:block" />
        <BreadcrumbItem>
          <BreadcrumbPage>{item?.label ?? "Not found"}</BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>
  );
}

/** Redirect legacy #tab deep links to shell routes (once, on first load). */
function useLegacyHashRedirect() {
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => {
    if (location.pathname !== "/") return;
    const hash = window.location.hash.split("/")[0];
    const target = HASH_REDIRECTS[hash];
    if (target) {
      const [path, keepHash] = target.split("#");
      navigate(path || "/", { replace: true });
      window.location.hash = keepHash ? `#${keepHash}` : "";
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

export default function ShellLayout() {
  useLegacyHashRedirect();
  const location = useLocation();
  const item = navItemForPath(location.pathname);
  const section = sectionForPath(location.pathname);
  const isTrading = section?.label === "Trading";

  return (
    <SidebarProvider>
      <ShellSidebar />
      <SidebarInset>
        <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-2 border-b border-border/60 bg-background/90 px-4 backdrop-blur">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <ShellBreadcrumb />
          <div className="ml-auto flex items-center gap-3">
            <LiveVitals />
            {item?.live && (
              <Badge variant="outline" className="hidden text-[10px] sm:inline-flex">
                live surface
              </Badge>
            )}
            <CommandPalette />
          </div>
        </header>
        <BackendStatusBanner />
        <main className="flex-1 overflow-auto">
          {isTrading && (
            <div className="px-4 pt-4">
              <RiskDisclaimer />
            </div>
          )}
          <RouteErrorBoundary key={location.pathname} name={item?.label ?? "This page"}>
            <Suspense fallback={<PageSkeleton />}>
              <Outlet />
            </Suspense>
          </RouteErrorBoundary>
          <SiteFooter />
        </main>
        <SupportProjectPrompt />
      </SidebarInset>
    </SidebarProvider>
  );
}
