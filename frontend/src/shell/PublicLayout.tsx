/**
 * PublicLayout — the marketing / public front door chrome.
 *
 * A light, backend-independent frame (top bar with the real wordmark + primary
 * navigation and an "Open console" call to action, then the routed public page, then
 * the shared SiteFooter). Distinct from the operator ShellLayout: this is what a
 * first-time visitor, investor, or reviewer sees before entering the console.
 */

import { Link, NavLink, Outlet } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { SiteFooter } from "./SiteFooter";
import { BrandMark } from "./Brand";
import { PRODUCT } from "./companyFacts";

const NAV = [
  { to: "/evidence", label: "Evidence" },
  { to: "/company", label: "Company" },
  { to: "/legal", label: "Legal" },
];

export default function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
          <Link to="/" className="flex items-center gap-2.5">
            <BrandMark size={32} className="shrink-0" />
            <span className="grid leading-tight">
              <span className="text-sm font-semibold tracking-wide">{PRODUCT.name}</span>
              <span className="text-[10px] text-muted-foreground">{PRODUCT.poweredBy}</span>
            </span>
          </Link>

          <nav className="ml-auto hidden items-center gap-1 sm:flex">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `border-b-2 px-3 py-1.5 text-sm transition-colors hover:text-foreground ${
                    isActive
                      ? "border-primary font-medium text-foreground"
                      : "border-transparent text-muted-foreground"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>

          <Button asChild size="sm" className="ml-auto sm:ml-2">
            <Link to="/console">Open console →</Link>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <SiteFooter />
    </div>
  );
}
