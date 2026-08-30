/**
 * Router — two sibling layouts:
 *   • PublicLayout (marketing front door): "/" landing, /legal, /evidence, /company.
 *     Backend-independent; what a first-time visitor or investor sees.
 *   • ShellLayout (operator console): every nav surface, unchanged paths. The Overview
 *     lives at /console (no longer the "/" index — that belongs to the landing).
 * Every page is lazy-loaded so each surface is its own chunk.
 */

import { lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import ShellLayout from "./ShellLayout";
import PublicLayout from "./PublicLayout";
import { AuthGate } from "@/components/AuthGate";
import { ALL_NAV_ITEMS } from "./nav";

const LandingPage = lazy(() => import("./pages/LandingPage"));
const LegalPage = lazy(() => import("./pages/LegalPage"));
const EvidencePage = lazy(() => import("./pages/EvidencePage"));
const CompanyPage = lazy(() => import("./pages/CompanyPage"));

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: "legal", element: <LegalPage /> },
      { path: "evidence", element: <EvidencePage /> },
      { path: "company", element: <CompanyPage /> },
    ],
  },
  {
    // The operator console is auth-gated (a no-op unless VITE_REQUIRE_AUTH=1);
    // the public PublicLayout subtree above stays open in every build.
    element: (
      <AuthGate>
        <ShellLayout />
      </AuthGate>
    ),
    children: ALL_NAV_ITEMS.map((item) => ({
      path: item.path.replace(/^\//, ""),
      element: <item.Component />,
    })),
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
