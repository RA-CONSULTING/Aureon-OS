# Aureon Documentation Index

Master table of contents for all project documentation.

> **New here?** Start with the [Navigation Guide](NAVIGATION_GUIDE.md) for guided paths by role.

## Audience Routes
| Audience | Document | Description |
|----------|----------|-------------|
| Investors | [Investor, Public, And Funder Guide](investor/README.md) | Formal diligence path, capability categories, claim discipline, and review sequence |
| Company & credentials | [Company Profile](../COMPANY.md) | R&A Consulting (NI696693), Aureon Zorza Technologies brand, Silver-level Innovate NI recognition, website |
| Public GitHub readers | [Repository README](../README.md) | Current front door with concise repo map and evidence posture |
| End users and integrators | [Repo-Wide Sitemap](REPO_SITEMAP.md) | Whole-repo organization, capability groups, related systems, and SaaS integration surfaces |
| End-user task navigation | [End-User Access Map](END_USER_ACCESS_MAP.md) | Task-based access to capabilities, docs, related systems, runtime surfaces, and safety gates |
| System integration map | [System Integration Map](SYSTEM_INTEGRATION_MAP.md) | System-by-system bindings for all 29 current implementation capabilities, access routes, entrypoints, public artifacts, validation references, and safety gates |
| Capability registry | [Capability Registry](CAPABILITY_REGISTRY.md) | Current capability table converted into resolved surfaces, runtime refs, systems, and access routes |
| Frontend repository map | [Repo Navigation Panel](../frontend/src/components/RepoNavigationPanel.tsx) | Console tab mounted at `#repo-map` for the public repo sitemap and end-user access map |
| File-level repo index | [Repo Navigation Index](repo_navigation_index.json) | Generated `git ls-files` index with categories, zones, capability IDs, and frontend public mirror |
| Directory organization tree | [Repo Organization Tree](repo_organization_tree.json) | Generated tracked-directory hierarchy with parent paths, categories, zones, capability IDs, and frontend public mirror |
| Navigation readiness audit | [Repo Navigation Readiness](repo_navigation_readiness.json) | Generated pass/fail audit for sitemap freshness, capability routing, system mapping, public mirrors, and SaaS blockers |
| Navigation completion audit | [Repo Navigation Completion Audit](repo_navigation_completion_audit.json) | Generated requirement-by-requirement proof for repo-wide navigation, capability routing, system mapping, and SaaS integration readiness |
| Capability access matrix | [Capability Access Matrix](capability_access_matrix.json) | Generated route matrix binding every current capability to end-user start points, systems, runtime/API surfaces, and safety gates |
| Capability registry manifest | [Capability Registry Manifest](capability_registry.json) | Generated capability contract mirrored to the frontend public folder |
| System integration manifest | [System Integration Manifest](system_integration_map.json) | Generated system-to-capability integration contract mirrored to the frontend public folder |
| SaaS integrators | [SaaS Integration Readiness](SAAS_INTEGRATION_READINESS.md) | End-user access matrix, env/config inventory, deploy surfaces, auth boundaries, and production gates |
| SaaS integration manifest | [SaaS Integration Manifest](saas_integration_manifest.json) | Generated env-name, deployment-surface, Supabase auth, and production-gate contract for SaaS shells |
| SaaS integration handoff | [SaaS Integration Handoff](saas_integration_handoff.json) | Generated implementer handoff for public manifests, deployment surfaces, env names, Supabase hardening, readiness gates, and release steps |
| Supabase hardening review | [Supabase Hardening Review](SUPABASE_HARDENING_REVIEW.md) | Production blocker review for public and JWT-gated Supabase Edge Functions |
| Supabase hardening manifest | [Supabase Hardening Manifest](supabase_hardening_manifest.json) | Generated Edge Function hardening contract mirrored to the frontend public folder |
| Operational manifests | [SaaS System Inventory](audits/aureon_saas_system_inventory.json) | Public-safe autonomous frontend manifest set for SaaS inventory, unification, evolution queue, runtime status, and capability switchboard |
| Grant and funder reviewers | [Gary/Aureon Metadata Research Inventory](../data/research/grants/applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_20260712_20260712_203741.md) | Categorized Gary/Aureon evidence inventory and copied research set |
| Terminology reviewers | [Formal Terminology](investor/TERMINOLOGY.md) | Translation from older internal language to investor-safe terminology |
| Historical review | [Legacy README Archive](archive/README_legacy_20260712.md) | Verbatim preserved README content from before the formal front-door update |

## Getting Started
| Document | Description |
|----------|-------------|
| [Repo-Wide Sitemap](REPO_SITEMAP.md) | Whole-repo organization, capability groups, related systems, and SaaS integration surfaces |
| [End-User Access Map](END_USER_ACCESS_MAP.md) | Task-based access to capabilities, docs, related systems, runtime surfaces, and safety gates |
| [System Integration Map](SYSTEM_INTEGRATION_MAP.md) | System-by-system integration view for current capability IDs, access routes, entrypoints, public artifacts, validation refs, and gates |
| [Capability Registry](CAPABILITY_REGISTRY.md) | Current capability registry generated from `CAPABILITIES.md` |
| [Repo Navigation Panel](../frontend/src/components/RepoNavigationPanel.tsx) | End-user console surface for the public repo map, capability routes, and navigation contract |
| [Repo Navigation Index](repo_navigation_index.json) | File-level repo index generated from `git ls-files` for searchable navigation |
| [Repo Organization Tree](repo_organization_tree.json) | Directory hierarchy generated from `git ls-files` for structural navigation |
| [Repo Navigation Readiness](repo_navigation_readiness.json) | Public readiness audit generated from the repo navigation and SaaS contracts |
| [Repo Navigation Completion Audit](repo_navigation_completion_audit.json) | Completion proof generated from the sitemap, organization tree, access matrix, system map, readiness audit, and SaaS handoff |
| [Capability Access Matrix](capability_access_matrix.json) | End-user route matrix for every current capability in `CAPABILITIES.md` |
| [Capability Registry Manifest](capability_registry.json) | Machine-readable capability registry used by the frontend repo map |
| [System Integration Manifest](system_integration_map.json) | Machine-readable system integration contract generated from repo maps |
| [SaaS Integration Readiness](SAAS_INTEGRATION_READINESS.md) | End-user access matrix, env/config inventory, deploy surfaces, auth boundaries, and production gates |
| [SaaS Integration Manifest](saas_integration_manifest.json) | Machine-readable SaaS integration contract generated from repo config |
| [SaaS Integration Handoff](saas_integration_handoff.json) | Machine-readable integration handoff used by the frontend repo map and implementer review |
| [Supabase Hardening Review](SUPABASE_HARDENING_REVIEW.md) | Human-readable blocker review for public Edge Functions and JWT-gated mutation routes |
| [Supabase Hardening Manifest](supabase_hardening_manifest.json) | Machine-readable Supabase hardening contract used by the frontend repo map |
| [Operational SaaS Inventory](audits/aureon_saas_system_inventory.json) | Mounted autonomous frontend manifest set for inventory, unification, evolution queue, runtime status, and switchboard visibility |
| [Navigation Contract Validator](../scripts/validation/validate_repo_navigation_contract.py) | Verifies public manifests, repo counts, Supabase auth counts, and key navigation links |
| [Navigation Guide](NAVIGATION_GUIDE.md) | Learning paths for traders, developers, researchers |
| [Quick Start](QUICK_START.md) | Get running in 10 minutes |
| [Windows Setup](windows/WINDOWS_SETUP_GUIDE.md) | Windows-specific installation |
| [Linux Setup](linux/LINUX_SETUP_GUIDE.md) | Native full Linux version — install + one-command launcher + systemd |
| [Scripts Index](SCRIPTS_INDEX.md) | Find the right startup script |

## Architecture & System Design
| Document | Description |
|----------|-------------|
| [Module Reference](MODULES_AT_A_GLANCE.md) | All 715 modules across 24 domains |
| [System Architecture Map](architecture/SYSTEM_ARCHITECTURE_MAP.md) | 5-phase startup hierarchy |
| [Aureon Operator Switchboard](architecture/AUREON_OPERATOR_SWITCHBOARD.md) | Runs many AIs (ChatGPT/Grok/Gemini) through the repo: ground → consensus → veto |
| [Feature Switchboard](architecture/FEATURE_SWITCHBOARD.md) | Turn every system feature on/off at human discretion — safe toggles + armed hard-boundary flags (gates never removed) |
| [Production-Grade Program](runbooks/PRODUCTION_GRADE.md) | Two-tier gate, serving surface, CI/Docker, and the repo-wide hardening ledger |
| [SaaS Platform](SAAS_PLATFORM.md) | Categorized catalog + domain adapters + honest status feeding the React console; Supabase tenancy bridge |
| [Intelligence Wiring Matrix](architecture/INTELLIGENCE_WIRING_MATRIX.md) | What intelligence feeds which trader |
| [Open Market Data Matrix](architecture/OPEN_MARKET_DATA_MATRIX.md) | Data feed topology |
| [Repo Mindmap](architecture/REPO_MINDMAP.md) | Complete file inventory |
| [Continuous Market Pipeline](architecture/CONTINUOUS_MARKET_WORLDVIEW_PIPELINE.md) | Always-on coherence system |
| [Theory to Code](architecture/THEORY_TO_CODE.md) | Research concepts → implementations |
| [System Landscape](architecture/SYSTEM_LANDSCAPE.md) | High-level subsystem overview |
| [HNC White Paper](HNC_UNIFIED_WHITE_PAPER.md) | Harmonic Nexus Core mathematical framework |

## Trading Operations
| Document | Description |
|----------|-------------|
| [Live Trading Runbook](LIVE_TRADING_RUNBOOK.md) | Day-to-day trading operations |
| [Dashboard Guide](dashboards/DASHBOARD_GUIDE.md) | Live monitoring dashboard |
| [Multi-Broker Guide](integrations/MULTI_BROKER_GUIDE.md) | Multi-exchange configuration |

## Sensor Suite (φ signal adapters)
| Document | Description |
|----------|-------------|
| [Sensor Suite](reports/SENSOR_SUITE.md) | **Start here** — every `aureon/bio/` lane (modality × boundary × data × benchmark) on one unchanged φ engine |
| [φ Celestial Observatory](reports/CELESTIAL_OBSERVATORY.md) | **The capstone** — one instrument operating every sky lane through the one engine, with the consolidated picture |
| [Human Harmonic Proxy](reports/HUMAN_HARMONIC_PROXY.md) | Core governed derived-signal scorer |
| [Sky Fingerprint](reports/SKY_FINGERPRINT.md) · [Faint Sky / UPE](reports/FAINT_SKY_UPE.md) · [NASA Sky Data](reports/NASA_SKY_DATA.md) | Astronomical light lanes |
| [Sky Map](reports/SKY_MAP.md) · [Cosmic Sensors](reports/COSMIC_SENSORS.md) · [Coherence Lane](reports/COHERENCE_LANE.md) | All-sky map + Schumann/planetary/space-weather + DE440 coherence |
| [Sacred Lattice](reports/SACRED_LATTICE.md) | The repo's OWN sky map — ancient-site coords + φ-geometry + Solfeggio/Schumann, gridded into an Earth-referenced map |
| [Harmonic Core](reports/HARMONIC_CORE.md) | The repo's OWN harmonic substrate — HNC Master Formula Λ(t) modes + Celtic Ogham + Ghost Dance ancestral tones |
| [Counter-Frequency](reports/COUNTER_FREQUENCY.md) | The repo's OWN φ/Fibonacci harmonic canon — Fibonacci ladder + golden-ratio harmonics + Solfeggio |
| [Market Fingerprint](reports/MARKET_FINGERPRINT.md) · [QGITA Calibration](reports/QGITA_CALIBRATION.md) | Market test-bed + QGITA φ calibration |

## Deployment
| Document | Description |
|----------|-------------|
| [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md) | General deployment |
| [DigitalOcean Guide](deployment/DIGITALOCEAN_DEPLOYMENT.md) | DigitalOcean App Platform |
| [Production Checklist](runbooks/PRODUCTION_CHECKLIST.md) | Pre-production validation |

## Research
| Document | Description |
|----------|-------------|
| [Ancient Convergence](research/ANCIENT_CONVERGENCE.md) | 12 civilizations, 47+ convergence points |
| [Bot Intelligence](research/BOT_INTELLIGENCE.md) | 23 algorithms, 37 firms profiled |
| [Financial Exposure](research/FINANCIAL_EXPOSURE.md) | Market extraction evidence |
| [Unified Field](research/UNIFIED_FIELD.md) | Connecting all domains |
| [Counter-Strategies](research/COUNTER_STRATEGIES.md) | How to fight back |

## Contributing
| Document | Description |
|----------|-------------|
| [Contributing Guide](CONTRIBUTING.md) | How to contribute |
| [Code of Conduct](CODE_OF_CONDUCT.md) | Community standards |
| [Changelog](CHANGELOG.md) | Version history |
