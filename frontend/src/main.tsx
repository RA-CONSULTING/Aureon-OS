import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import { initNetworkMonitoring } from "./core/networkMonitor";
import { ThemeProvider } from "./components/theme-provider";
import { TooltipProvider } from "./components/ui/tooltip";
import { Toaster } from "./components/ui/toaster";
import { Toaster as Sonner } from "./components/ui/sonner";
import { router } from "./shell/routes";
import { setAuthTokenProvider } from "./services/apiClient";
import { supabase } from "./integrations/supabase/client";

// Initialize network monitoring before app renders
initNetworkMonitoring();

// Forward the end-user session token to every /api/* call so the operator can
// identify the tenant. No session ⇒ no header ⇒ single-operator path unchanged.
setAuthTokenProvider(async () => {
  try {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  } catch {
    return null;
  }
});

const queryClient = new QueryClient();

// Providers wrap the whole app. Auth is enforced per-route (the operator console
// only) inside the router, so the public front door stays open even in production;
// the support-the-project card is mounted inside the console, not globally.
createRoot(document.getElementById("root")!).render(
  <ThemeProvider defaultTheme="dark">
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <RouterProvider router={router} />
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);
