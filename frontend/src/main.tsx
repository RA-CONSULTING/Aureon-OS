import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { initNetworkMonitoring } from "./core/networkMonitor";
import { AuthGate } from "./components/AuthGate";
import { SupportProjectPrompt } from "./components/SupportProjectPrompt";

// Initialize network monitoring before app renders
initNetworkMonitoring();

// AuthGate is a no-op unless VITE_REQUIRE_AUTH=1 (the production build sets it).
// SupportProjectPrompt is the timer-based, non-blocking support-the-project card.
createRoot(document.getElementById("root")!).render(
  <AuthGate>
    <App />
    <SupportProjectPrompt />
  </AuthGate>
);
