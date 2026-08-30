import { defineConfig, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // The React app talks to the Aureon operator's REST surface over relative
  // `/api/...` paths (see src/services/apiClient.ts). In dev the operator runs
  // as a separate process, so proxy `/api` to it. Target + optional bearer are
  // env-configurable so the client code never carries a token.
  const operatorUrl = process.env.VITE_OPERATOR_URL || "http://localhost:8080";
  const operatorToken =
    process.env.VITE_OPERATOR_TOKEN || process.env.AUREON_OPERATOR_API_KEY || "";
  const apiProxy: ProxyOptions = {
    target: operatorUrl,
    changeOrigin: true,
    // Bearer is injected here (not in client code) so a secured operator
    // (AUREON_OPERATOR_API_KEY set) still works without leaking the token.
    configure: (proxy) => {
      if (!operatorToken) return;
      proxy.on("proxyReq", (proxyReq) => {
        proxyReq.setHeader("Authorization", `Bearer ${operatorToken}`);
      });
    },
  };

  return {
  server: {
    host: "0.0.0.0",
    // Dev server runs on 8088 so the operator can keep its default 8080 (the
    // proxy target below). Playwright uses 8081; nothing else pins 8080 here.
    port: 8088,
    proxy: {
      "/api": apiProxy,
      "/healthz": apiProxy,
      "/readyz": apiProxy,
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: [
      {
        find: /^@\/integrations\/supabase\/client$/,
        replacement: path.resolve(__dirname, "./src/integrations/supabase/client.ts"),
      },
      {
        find: "@",
        replacement: path.resolve(__dirname, "./src"),
      },
    ],
  },
  build: {
    // The big trading/console route chunks (WarRoom, LegacyConsole) and recharts
    // legitimately exceed 500 kB; raise the warning bar so real regressions stand
    // out instead of drowning in expected noise. Splitting them further is staged.
    chunkSizeWarningLimit: 800,
    // Route-level chunks come from React.lazy in src/shell/nav.ts; these split
    // the big vendor groups so no chunk carries the whole platform.
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-radix": [
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-popover",
            "@radix-ui/react-scroll-area",
            "@radix-ui/react-select",
            "@radix-ui/react-tabs",
            "@radix-ui/react-toast",
            "@radix-ui/react-tooltip",
          ],
          "vendor-charts": ["recharts"],
          "vendor-supabase": ["@supabase/supabase-js"],
        },
      },
    },
  },
  };
});
