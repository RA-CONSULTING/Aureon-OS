# APPLICATION TEMPLATE B: AQTS → Invest NI Grant for R&D
## Product: AQTS (Adaptive Quantitative Trading System)
## Funder: Invest NI — Grant for Research and Development
## Deadline: Rolling (must be Invest NI client first — call 0800 181 4422)
## Amount: £50K–£200K (SME tier)
## Eligibility: R&A CONSULTING (NI696693) — YES, NI-registered SME

---

### SECTION 1: APPLICANT DETAILS (Pre-filled)

**Company Name:** R&A CONSULTING AND BROKERAGE SERVICES LTD
**Company Number:** NI696693
**Registered Address:** 1 Quadrant Place, Belfast, BT12 4HX, Northern Ireland
**Company Status:** Active | Incorporated: 1 March 2021
**Innovate NI Status:** Silver Level Innovator
**Contact Email:** [FILL IN]
**Phone:** [FILL IN]
**Website:** [FILL IN]

**Lead Applicant:** Łukasz Zuchowski
**Role:** Chief Research Specialist
**Email:** [FILL IN]
**Phone:** [FILL IN]

**Team Size:** 2 (expandable to 4 with grant funding)

---

### SECTION 2: PROJECT SUMMARY (200 words max)

**AQTS** is a multi-agent quantitative trading system that uses adaptive reinforcement learning to optimize portfolio performance across crypto and traditional asset markets. Unlike static trading bots, AQTS dynamically adjusts strategy parameters based on real-time market conditions, risk tolerance, and cross-asset correlation.

**Technical Innovation:**
- Multi-agent architecture: 3 specialized bots (trend, mean-reversion, arbitrage) coordinate via weighted consensus
- Adaptive risk management: Position sizing scales with volatility and drawdown history
- Cross-market correlation: Detects regime shifts across crypto, forex, and equity markets
- Real-time backtesting: Strategy validation against 5-year historical data before live deployment

**Commercial Potential:**
Target market: retail traders, small hedge funds, and family offices who need institutional-grade quant tools without institutional budgets. SaaS pricing: £50–£200/month per user.

**Grant Use:**
Funding will support: (1) exchange API integration (Binance, Kraken, Coinbase), (2) risk management dashboard, (3) strategy marketplace, (4) regulatory compliance (FCA sandbox application).

---

### SECTION 3: TECHNICAL APPROACH (400 words max)

**Architecture:**
AQTS uses a modular multi-agent system: Market Data Layer → Signal Generator → Risk Engine → Position Manager → Execution Layer → Performance Tracker.

**Key Components:**
1. **Trend Bot:** Moving average convergence, momentum indicators, volume analysis. Timeframe: 1h–4h.
2. **Mean Reversion Bot:** Bollinger Bands, RSI divergence, statistical arbitrage. Timeframe: 15m–1h.
3. **Arbitrage Bot:** Cross-exchange price discrepancy, funding rate arbitrage, triangular arbitrage. Timeframe: real-time.
4. **Consensus Engine:** Weighted voting across all three bots based on recent performance accuracy. Adaptive weights.
5. **Risk Manager:** Kelly criterion, max drawdown limits, correlation heatmap, VaR calculation.

**Innovation vs. State of the Art:**
Current retail trading bots use single-strategy approaches. AQTS is the first open-source multi-agent system with adaptive consensus and cross-market correlation detection.

**Technical Risk:**
Low. Core architecture is built (React frontend, Python backend, 3 trading bots operational). Risk is exchange integration and regulatory compliance, not fundamental research.

---

### SECTION 4: MARKET AND COMMERCIALISATION (250 words max)

**Target Market:** UK and EU retail traders, small hedge funds, family offices.

**Market Size:**
- Global algorithmic trading market: $15.77B (2024), growing at 10.7% CAGR
- UK retail crypto trading: 5.2M active traders (2024)
- Target: 1% of UK retail market = 52,000 potential users

**Competitors:**
- 3Commas (cloud-dependent, closed source, $29–$99/month)
- Cryptohopper (cloud-dependent, limited strategy customization)
- TradingView (charting only, no execution)

**Competitive Advantage:**
- Local-first (data stays on user's machine)
- Multi-agent adaptive consensus (no competitor has this)
- Open source core (community trust)
- UK/EU regulatory focus (FCA compliance built-in)

**Revenue Model:**
- SaaS subscription: £50–£200/month
- Strategy marketplace: 20% commission on paid strategies
- Enterprise licensing: £5K–£20K/year for hedge funds

---

### SECTION 5: PROJECT PLAN AND MILESTONES

| Phase | Duration | Activities | Deliverables | Cost |
|-------|----------|------------|--------------|------|
| 1 | Months 1–3 | Exchange API integration, backtesting engine | 3 exchange connectors, backtest suite | £XXK |
| 2 | Months 4–6 | Risk dashboard, strategy marketplace | Web UI, strategy store | £XXK |
| 3 | Months 7–9 | FCA sandbox application, compliance | Regulatory approval, audit | £XXK |
| 4 | Months 10–12 | Launch, marketing, customer acquisition | 100 paying customers, £5K MRR | £XXK |

**Total Grant Request:** [FILL IN: £50K–£100K recommended]
**Match Funding:** [FILL IN: 10-20%]

---

### SECTION 6: TEAM AND CAPABILITY

**GARY LECKEY — Director:**
[FILL IN: Background in trading, quantitative analysis, business development]

**Łukasz Zuchowski — Chief Research Specialist:**
Expert in AI-assisted systems, multi-model convergence, and software architecture. Lead developer of AQTS and AOIA-Core.

**Planned Hires:**
- Quantitative Developer (Month 3): £50K/year
- Regulatory Compliance Officer (Month 6): £45K/year

---

### SECTION 7: FINANCIAL INFORMATION

[Same as Template A — copy across]

---

### SECTION 8: ADDITIONAL INFORMATION

**Intellectual Property:**
- AQTS: MIT License (open source)
- All code: github.com/RA-CONSULTING/aureon-trading (or Lukasz's repo)

**Risks:**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Exchange API changes | High | Medium | Modular design, multiple exchanges |
| Regulatory rejection | Medium | High | Early engagement with FCA |
| Market downturn | Medium | Medium | Multi-asset, not crypto-only |

---

**CHECKLIST BEFORE SUBMISSION:**
- [ ] All [FILL IN] sections completed
- [ ] Must be Invest NI client first (call 0800 181 4422)
- [ ] No HNC language used
- [ ] Budget adds up
- [ ] Match funding confirmed

---

**Compiled for:** Łukasz Zuchowski  
**Date:** 2026-07-05
