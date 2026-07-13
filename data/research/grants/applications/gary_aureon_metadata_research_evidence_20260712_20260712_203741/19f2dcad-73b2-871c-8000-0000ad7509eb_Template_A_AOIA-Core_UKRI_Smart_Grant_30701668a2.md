# APPLICATION TEMPLATE A: AOIA-Core → UKRI Smart Grant
## Product: AOIA-Core (Adaptive Oceanic Intelligence Architecture)
## Funder: UKRI Innovate UK — Smart Grant Q2 2026
## Deadline: 17 July 2026 (full proposal)
## Amount: Up to £2M for R&D (SME stream: £25K–£500K)
## Eligibility: R&A CONSULTING (NI696693) — YES, UK SME eligible

---

### SECTION 1: APPLICANT DETAILS (Pre-filled)

**Company Name:** R&A CONSULTING AND BROKERAGE SERVICES LTD
**Company Number:** NI696693
**Registered Address:** 1 Quadrant Place, Belfast, BT12 4HX, Northern Ireland
**Company Status:** Active | Incorporated: 1 March 2021
**Innovate NI Status:** Silver Level Innovator
**Contact Email:** [FILL IN: gaxlec@gmail.com OR tonystarrkarc@gmail.com]
**Phone:** [FILL IN]
**Website:** [FILL IN: GitHub link or company site]

**Lead Applicant:** Łukasz Zuchowski
**Role:** Chief Research Specialist
**Email:** [FILL IN: Lukasz's email]
**Phone:** [FILL IN]

**Team Size:** 2 (expandable to 4 with grant funding)
**Current Employees:** GARY LECKEY (Director), Łukasz Zuchowski (Chief Research Specialist)
**Planned Hires with Grant:** 2 additional engineers (AI/ML + DevOps)

---

### SECTION 2: PROJECT SUMMARY (250 words max)

[WRITE THIS SECTION — Use the following scientific language, NOT HNC terminology]

**AOIA-Core** is a local-first AI runtime architecture that enforces evidence boundaries between human operators and large language model outputs. Unlike cloud-dependent AI systems, AOIA-Core runs entirely on local hardware, ensuring data sovereignty, privacy, and reproducibility.

**Technical Innovation:**
- Evidence-provenance tracking: Every model output is tagged with source attribution, confidence scoring, and contradiction detection
- Human-in-the-loop execution: All consequential actions require explicit human approval before execution
- Cross-model validation: Outputs are validated against multiple model providers (OpenAI, Anthropic, local models) to detect hallucination and bias
- Contradiction resolution: Built-in semantic diff engine identifies and flags conflicting information across model responses

**Market Need:**
Enterprise AI adoption is blocked by three concerns: (1) data leakage to cloud providers, (2) inability to audit model outputs, and (3) hallucination risk in high-stakes decisions. AOIA-Core addresses all three by keeping data local, tracking provenance, and requiring human validation.

**Commercial Potential:**
Target market: SMEs in regulated sectors (legal, healthcare, finance) who need AI assistance but cannot risk cloud data exposure. Initial customers: [FILL IN: any pilot customers or LOIs].

**Grant Use:**
Funding will support: (1) developer tooling and IDE integration, (2) enterprise deployment packaging, (3) security audit and certification, (4) pilot customer onboarding.

---

### SECTION 3: TECHNICAL APPROACH (500 words max)

[WRITE THIS SECTION — Expand on the following points]

**Architecture:**
AOIA-Core uses a modular pipeline: Input → Retrieval → Evidence Assembly → Model Query → Provenance Tagging → Contradiction Check → Human Approval → Execution.

**Key Components:**
1. **Provenance Engine:** Tracks every model output to its source, temperature, model version, and timestamp. Uses W3C PROV standards.
2. **Contradiction Detector:** Semantic similarity + logical consistency checks across multiple model outputs. Flags disagreements for human review.
3. **Authority Scope:** Defines which actions the AI can take autonomously vs. which require human approval. Configurable per-deployment.
4. **Memory Ontology:** Structured knowledge graph for long-term memory across sessions, with versioning and rollback.
5. **Runtime Map:** Real-time visualization of data flow, model decisions, and evidence chains.

**Innovation vs. State of the Art:**
Current solutions (LangChain, LlamaIndex) provide chains but not evidence boundaries. AOIA-Core is the first open-source framework that makes provenance and human approval mandatory, not optional.

**Technical Risk:**
Low. Core architecture is built (38 commits, 31 tags, MIT license). Risk is integration and packaging, not fundamental research.

---

### SECTION 4: MARKET AND COMMERCIALISATION (300 words max)

[WRITE THIS SECTION]

**Target Market:** UK SMEs in regulated sectors (legal, healthcare, finance, public sector) who need AI assistance but cannot use cloud-based solutions due to GDPR, data protection, or security requirements.

**Market Size:** [FILL IN: TAM, SAM, SOM figures]

**Competitors:**
- LangChain (cloud-dependent, no provenance)
- LlamaIndex (cloud-dependent, no human approval)
- Private AI (closed source, expensive)

**Competitive Advantage:**
AOIA-Core is the ONLY open-source, local-first, evidence-bound AI framework. Competitors are either cloud-dependent or closed-source.

**Revenue Model:**
- Open-source core (free) → enterprise support contracts (£5K–£20K/year)
- SaaS deployment service (managed on-premise)
- Training and certification

**Pilot Customers:** [FILL IN: Any LOIs or expressions of interest]

---

### SECTION 5: PROJECT PLAN AND MILESTONES (Gantt-style)

| Phase | Duration | Activities | Deliverables | Cost |
|-------|----------|------------|--------------|------|
| 1 | Months 1–3 | Developer tooling, IDE plugin | VS Code extension, CLI v1.0 | £XXK |
| 2 | Months 4–6 | Enterprise packaging, Docker/K8s | Deployment templates, security audit | £XXK |
| 3 | Months 7–9 | Pilot customer onboarding | 3 pilot deployments, case studies | £XXK |
| 4 | Months 10–12 | Commercial launch, marketing | Website, documentation, sales | £XXK |

**Total Grant Request:** [FILL IN: £50K–£200K recommended for first application]
**Match Funding:** [FILL IN: 10-20% from R&A CONSULTING or other sources]

---

### SECTION 6: TEAM AND CAPABILITY

**GARY LECKEY — Director:**
[FILL IN: 2-3 sentences about GARY's background, experience, role in the company]

**Łukasz Zuchowski — Chief Research Specialist:**
Self-taught AI researcher with expertise in multi-model LLM convergence, epistemic risk analysis, and AI-assisted scientific development. Lead developer of AOIA-Core, MHLM convergence framework, and LSC neutrino anomaly detection model. Published research on Zenodo (record 19941506).

**Planned Hires:**
- AI/ML Engineer (Month 3): £45K/year
- DevOps/Security Engineer (Month 4): £50K/year

---

### SECTION 7: FINANCIAL INFORMATION

**Company Turnover:** [FILL IN: Last 2 years]
**Profit/Loss:** [FILL IN]
**Bank Details:** [FILL IN]
**Funding History:** [FILL IN: Any previous grants or investments]

---

### SECTION 8: ADDITIONAL INFORMATION

**Intellectual Property:**
- AOIA-Core: MIT License (open source)
- All code: github.com/luciferprosun/AOIA-Core
- No patents filed (open-source strategy)

**Ethical and Social Impact:**
- Local-first = reduced cloud energy consumption
- Evidence boundaries = reduced AI hallucination harm
- Open source = democratized AI access for SMEs

**Risks and Mitigation:**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Technical integration delays | Medium | Medium | Phased approach, MVP first |
| Market adoption slow | Medium | High | Pilot customers before launch |
| Competitor response | Low | Medium | First-mover advantage, open source |

---

## CHECKLIST BEFORE SUBMISSION

- [ ] All [FILL IN] sections completed
- [ ] Company documents attached (registration, UTR, bank details)
- [ ] Financial accounts attached (last 2 years)
- [ ] GitHub repo link verified and public
- [ ] No HNC language used anywhere in the application
- [ ] Word count checked for each section
- [ ] Budget adds up to total requested
- [ ] Match funding confirmed
- [ ] Deadline: 17 July 2026 — submit 3 days early to avoid technical issues

---

**Compiled for:** Łukasz Zuchowski  
**Date:** 2026-07-05  
**Template Version:** 1.0
