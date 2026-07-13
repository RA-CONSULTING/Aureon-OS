import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import { initNetworkMonitoring } from "./core/networkMonitor";
import { ThemeProvider } from "./components/theme-provider";
import { TooltipProvider } from "./components/ui/tooltip";
import { Toaster } from "./components/ui/toaster";
import { Toaster as Sonner } from "./components/ui/sonner";
import { AuthGate } from "./components/AuthGate";
import { SupportProjectPrompt } from "./components/SupportProjectPrompt";
import { router } from "./shell/routes";

// Initialize network monitoring before app renders
initNetworkMonitoring();

const queryClient = new QueryClient();

// Providers wrap the whole shell so every routed surface gets them.
// AuthGate is a no-op unless VITE_REQUIRE_AUTH=1 (the production build sets it).
// SupportProjectPrompt is the timer-based, non-blocking support-the-project card.
createRoot(document.getElementById("root")!).render(
  <ThemeProvider defaultTheme="dark">
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <AuthGate>
          <RouterProvider router={router} />
          <SupportProjectPrompt />
        </AuthGate>
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);
