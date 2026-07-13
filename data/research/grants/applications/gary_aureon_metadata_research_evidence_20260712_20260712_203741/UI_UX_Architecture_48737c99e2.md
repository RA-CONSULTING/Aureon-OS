# Aureon Trading Bot — Web Interface Map

This document provides a detailed blueprint for the Aureon Quantum Trading System (AQTS) web experience. It maps the navigation structure, primary user journeys, page layouts, core components, and supporting guidelines required to deliver a conversion-driven marketing surface and an operations-grade trading console.

---

## 1. Audience & Role Alignment

| Role | Primary Goals | Web Surfaces Used | Notes |
| --- | --- | --- | --- |
| **Prospect / Trial User** | Understand the value proposition, request access, explore demo data. | Landing page, marketing modals, guided tour mode. | No exchange connection allowed. Focus on education and lead capture. |
| **Retail Trader (Starter)** | Connect one exchange, monitor signals, manually execute trades, review P&L. | Dashboard, Signals, Live Terminal, Trade History. | Paper/live toggle visible but automation locked. |
| **Pro Subscriber** | Run automated strategies, manage risk, diversify across exchanges, track performance. | Bot Configuration, Portfolio, Analytics, Alerts. | Access to automation controls and advanced analytics. |
| **Enterprise Admin** | Onboard teams, manage seats, monitor SLA metrics, integrate APIs. | Enterprise Console (Settings, Integrations, Audit Logs). | White-label controls and API token management. |

---

## 2. High-Level Navigation Map

```
Top Bar (global)
 ├─ Aureon logo → Dashboard
 ├─ Quick pair ticker (BTC/USDT, ETH/USDT)
 ├─ Bot status pill (🟢 Live • 🟡 Paper • 🔴 Paused)
 ├─ Global search (⌘K)
 └─ Profile menu → Account, Billing, Support, Sign out

Left Sidebar (primary navigation)
 1. Dashboard
 2. Live Trading Terminal
 3. Signals & Alerts
 4. Bot Configuration
 5. Portfolio
 6. Analytics
 7. Trade History
 8. Integrations
 9. Learning Hub
10. Settings

Utility Drawer (right side, slide-over)
 ├─ Notifications feed
 ├─ Task checklist (onboarding, compliance)
 └─ Support chat / knowledge base
```

- **Responsive behavior:** Sidebar collapses to icon-only at ≥1280px width, hides behind hamburger under 1024px. Top bar elements stack for tablet, convert to overflow menu on mobile.

---

## 3. Core User Journeys (Web)

### 3.1 Onboarding & Trial Conversion
1. Landing page CTA → "Start Free Trial" modal.
2. Create account → email verification.
3. Guided tour overlay introduces Dashboard, Signals, Configuration.
4. "Connect Exchange" checklist item remains locked until plan upgrade.
5. Demo data populates charts; prompts highlight upgrade benefits.

### 3.2 Exchange Connection & Verification
1. User navigates to **Integrations**.
2. Choose exchange card (Binance, Coinbase, Kraken, Bybit).
3. Click "Connect" → drawer with instructions, API scopes, security tips.
4. Input API key/secret, optional IP whitelist, label connection.
5. Test connection → success badge + last sync timestamp.
6. Integration status surfaces across Dashboard + Portfolio.

### 3.3 Launching Automated Trading
1. Enter **Bot Configuration**.
2. Toggle trading mode → select *Paper* or *Live*.
3. Choose trading pairs (multi-select with liquidity hints).
4. Set risk parameters (sliders with numeric inputs + warning thresholds).
5. Adjust QGITA controls (Fibonacci depth, Lighthouse threshold, minimum consensus).
6. Press "Deploy Strategy" → confirmation modal summarising key settings.
7. Bot status pill updates globally; log entry created in Audit trail.

### 3.4 Monitoring & Intervention
1. **Dashboard** shows real-time KPIs and alerts.
2. Signals feed allows one-click manual execution or snooze.
3. Live Terminal provides chart overlays, order book, active orders.
4. Portfolio balance and risk heatmap highlight exposure by exchange/pair.
5. Emergency controls (Pause, Close All Positions) accessible from top bar and Dashboard widget.

### 3.5 Post-Trade Analysis
1. Navigate to **Analytics** → review equity curve, drawdown, Sharpe ratio.
2. Drill into **Trade History** → filter by pair/date/outcome.
3. Trade detail drawer reveals Lighthouse metrics, exit reason, fees.
4. Export CSV/PDF or schedule email report.

---

## 4. Page-Level Blueprints

### 4.1 Marketing Landing Page
- **Hero**: Headline, subhead, CTA buttons (Start Free Trial / Book Demo), background animation referencing Fibonacci lattice.
- **Problem → Solution**: Three-column pain points followed by QGITA framework explanation.
- **Feature Grid**: Six cards highlighting detection engine, automation, analytics, security, integrations, support.
- **Proof Section**: Testimonials, performance badges, compliance logos.
- **Pricing Table**: Free trial, Starter, Pro, Enterprise with feature comparison.
- **FAQ & Compliance**: Accordion covering security, risk, legal statements.
- **Final CTA**: Sticky footer with sign-up button, Telegram community link.

### 4.2 Dashboard (Home)
- **Top Metrics Strip**: Total P&L, Win Rate, Active Trades, Today's Signals (color-coded chips).
- **Equity Curve Card**: Toggle between net P&L, drawdown, benchmark; includes annotation markers for Lighthouse events.
- **Active Positions Table**: Inline controls for adjusting stops; contextual tooltips show risk per trade.
- **Signals Stream**: Real-time list with consensus score, time-to-expiry, quick action buttons (Execute, Ignore, Snooze, View Metrics).
- **System Health Widget**: Exchange connection status, API latency, last heartbeat, CPU/memory usage.
- **Tasks & Announcements**: Onboarding checklist, release notes.

### 4.3 Live Trading Terminal
- **Primary Chart Area**: TradingView widget with AQTS overlay (FTCP markers, Fibonacci lattice, Lighthouse heatmap).
- **Order Entry Module**: Tabs for Market, Limit, Conditional; includes risk preview, stop-loss/take-profit autopopulation.
- **Lighthouse Metrics Panel**: Five-bar visualization (linear, nonlinear, cross-scale, geometric, anomaly) + aggregate score dial.
- **Order Book & Recent Trades**: Depth ladders with iceberg detection, trade tape with whale alerts.
- **Position Management Drawer**: Modify stops, partial close, reverse position.

### 4.4 Signals & Alerts
- **Signal Cards**: Title, pair, direction, confidence, recommended action, supporting metrics.
- **Filters**: Timeframe, pair, confidence range, signal type (entry/exit/risk warning).
- **Notification Settings**: Matrix of delivery methods vs. event types; preview of Telegram/Email template.
- **Automation Rules**: If-this-then-that builder for customizing bot reactions to signals.

### 4.5 Bot Configuration
- **Mode Selector**: Paper vs Live with status description, last switch time, compliance acknowledgement.
- **Strategy Presets**: Conservative, Balanced, Aggressive, Custom; quick load & save user presets.
- **Risk Control Panel**: Sliders + numeric inputs for risk per trade, max daily loss, trailing stop, leverage (if derivatives).
- **QGITA Engine Settings**: Lattice depth selector, curvature window size, Lighthouse consensus threshold, metric weighting (sum enforced to 100%).
- **Validation Output**: Real-time backtest summary (expected win rate, average drawdown) recalculated on parameter change.

### 4.6 Portfolio
- **Capital Allocation Ring**: Distribution across exchanges and stablecoins vs deployed capital.
- **Balance Table**: Asset, free balance, in-position, value in base currency, percent of portfolio.
- **Transfers Panel**: Buttons linking out to exchange deposit/withdraw pages with security reminders.
- **Exposure Heatmap**: Pair vs exchange matrix showing open risk.

### 4.7 Analytics
- **KPIs Grid**: Profit factor, expectancy, average trade P&L, longest win/loss streaks.
- **Equity & Drawdown Charts**: Toggle for cumulative vs daily returns; underwater chart for drawdowns.
- **Trade Distribution**: Histograms by outcome, holding time, time-of-day, day-of-week.
- **Scenario Simulator (Future)**: Input hypothetical adjustments, see projected outcomes.

### 4.8 Trade History
- **Data Table**: Search, filters, column chooser, pagination; columns for ID, pair, side, entry, exit, size, fees, P&L.
- **Detail Drawer**: Candle snapshot, Lighthouse signal context, notes, execution log.
- **Exports & API**: Quick export dropdown (CSV, XLSX, JSON), API endpoint link for Enterprise users.

### 4.9 Integrations
- **Exchange Cards**: Connection state, permissions summary, last sync, API key mask, edit/remove actions.
- **Messaging Hooks**: Telegram, Discord, Slack, Email; token input and test message button.
- **Webhooks**: Endpoint creation with secret management and delivery log.

### 4.10 Settings & Support
- **Profile**: Contact info, timezone, language, notification defaults.
- **Security**: Password reset, 2FA, API key overview, login history.
- **Billing**: Plan overview, invoices, upgrade/cancel flow, payment method management.
- **Team Management (Enterprise)**: Seat assignments, role control, invitation flow.
- **Support Center**: Embedded knowledge base search, ticket submission, SLA indicator.

---

## 5. Component Library (Web)

| Component | Description | Pages Used |
| --- | --- | --- |
| **Status Pill** | Color-coded label with icon (e.g., `🟢 Live`). | Top bar, Dashboard widgets, Integrations. |
| **Metric Card** | Numeric KPI + sparkline + trend delta. | Dashboard, Analytics. |
| **Signal Card** | Direction badge, confidence ring, action buttons. | Signals, Notifications drawer. |
| **Tabular Data Grid** | Sortable, filterable table with sticky header. | Trade History, Portfolio balances. |
| **Drawer / Slide-over** | Secondary context without leaving page. | Integrations connect flow, Trade details. |
| **Confirmation Modal** | Summaries with checklist and double-confirm for high-risk actions. | Deploy bot, close all positions. |
| **Toast Notification** | Lightweight confirmation/errors top-right. | Global. |
| **Tooltip / Info Popover** | Explanations for advanced metrics. | Configuration, Analytics. |

Design tokens:
- **Spacing:** 8px baseline grid.
- **Border Radius:** 12px cards, 8px inputs, 999px pills.
- **Elevation:** 0/2/6/12 shadow scale for hover/focus.
- **Typography:** Heading `Inter 700`, body `Inter 500/400`, monospace `JetBrains Mono` for metrics.

---

## 6. Responsive Considerations

| Breakpoint | Layout Adjustments |
| --- | --- |
| ≥1440px (Wide) | Sidebar expanded with labels, multi-column dashboards, additional analytics cards visible. |
| 1280px | Default desktop. Sidebar collapsible, charts maintain 16:9 ratio. |
| 1024px (Tablet) | Sidebar hidden by default; accessible via hamburger. Widgets stack; charts switch to single-column. |
| 768px (Large Mobile) | Top metrics convert to swipeable carousel; tables become cards with disclosure toggles. |
| ≤480px (Mobile) | Critical controls only; automation toggles require long-press confirmation. |

---

## 7. Data & State Management

- **Real-time Data:** WebSockets for market data, signals, bot status. Fallback polling every 5 seconds when socket unavailable.
- **Global State:** Redux Toolkit (or Zustand) for session data, configuration drafts, notification queue.
- **Caching:** SWR/React Query for REST endpoints (analytics, history) with stale-while-revalidate.
- **Error Handling:** Top-level boundary with recovery instructions, inline error states for forms, retriable actions.

---

## 8. Accessibility & Compliance

- WCAG 2.1 AA contrast ratios (especially dark mode).
- Keyboard navigation: Tab order aligned with visual flow; skip-to-content link at top.
- ARIA labels for charts and live regions for streaming data.
- Tooltips and popovers accessible via keyboard (focus + ESC to dismiss).
- Localization-ready copy and date/number formatting respecting user timezone.
- Financial disclaimers surfaced on landing page, onboarding, and within Live mode toggles.

---

## 9. Implementation Roadmap (Web-first)

| Phase | Duration | Focus | Deliverables |
| --- | --- | --- | --- |
| **Phase 1 – Foundation** | Weeks 1-3 | Design system, layout scaffolding, routing. | Figma mocks, React layout components, responsive shell. |
| **Phase 2 – Trading Console** | Weeks 4-7 | Dashboard, Live Terminal, Signals, Configuration. | Integrated chart widgets, WebSocket data hooks, risk controls. |
| **Phase 3 – Analytics & History** | Weeks 8-10 | Portfolio, Analytics, Trade History, exports. | Data tables, charts, reporting API integration. |
| **Phase 4 – Integrations & Billing** | Weeks 11-14 | Exchange connectors UI, subscription management, support center. | API key flows, billing UI, documentation hub. |

---

## 10. Hand-off Checklist

- [ ] Finalized sitemap & navigation approved.
- [ ] Figma file with desktop/tablet/mobile breakpoints for all critical pages.
- [ ] Component library annotated with states (default, hover, active, error).
- [ ] Content inventory (copy doc) aligned with legal/compliance requirements.
- [ ] Accessibility audit (contrast, keyboard paths) signed off.
- [ ] Frontend backlog created with user stories tied to this map.

---

This map should be the reference for design, development, and product teams as they implement the AQTS web application. Any updates to flows or scope should be reflected here to maintain alignment across stakeholders.
