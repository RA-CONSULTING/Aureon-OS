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

// Initialize network monitoring before app renders
initNetworkMonitoring();

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
