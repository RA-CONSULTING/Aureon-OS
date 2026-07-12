# Aureon Formal Terminology

This document maps older internal language to terminology suitable for
investors, public GitHub readers, grant reviewers, and technical diligence.

The goal is not to erase project history. The goal is to make the current repo
readable without requiring reviewers to understand legacy metaphors first.

## Preferred Terms

| Legacy or internal term | Preferred public term | Notes |
|---|---|---|
| Organism | Operator runtime | Use when describing the full local system that coordinates services, evidence, and workflows. |
| Queen / Queen layer | Orchestration layer or review policy layer | Use only as a historical module name when referring to exact files. |
| Hive / hive mind | Multi-agent coordination or parallel worker coordination | Use for worker routing, shared state, and task distribution. |
| War room | Operations console | Use for dashboards, monitoring, and operator review screens. |
| Kill cycle | Execution workflow or order lifecycle | Use for trading or operational sequences that move from signal to review to action. |
| Flameborn | Operator console | Keep the product/module name where necessary, but describe its function formally. |
| Azyra automation | Warehouse operations automation | Use for controlled warehouse support workflows. |
| ThoughtBus / Mycelium | Event bus, state bus, or metadata fabric | Keep exact names only where they identify files or modules. |
| HNC / Auris | Evidence coherence and routing framework | Use when describing validation, prompt support, routing, or proof-state reasoning. |
| Mutation | Controlled live action | Use for any workflow that changes external state. |
| Autonomous | Operator-controlled automation | Use unless the route has evidence that it is fully automated and safely gated. |
| Attack lab | Authorized security test lab | Use only for authorized testing contexts. |
| Daemon | Background service | Use for long-running local processes. |

## Status Terms

| Term | Meaning |
|---|---|
| Current capability | Supported by code, docs, tests, or runbooks in the repository. |
| Evidence-backed claim | Supported by a specific file, ledger, report, screenshot, test, or command. |
| Prototype | Implemented enough to inspect or test, but not presented as a finished product. |
| Research hypothesis | Exploratory work that needs independent validation before commercial claims are made. |
| Operator-controlled | The system prepares or routes work, while human review or credentials gate sensitive action. |
| Archived | Preserved for audit history and continuity, not current front-door positioning. |

## Front-Facing Wording Rules

- Prefer concrete nouns: platform, runtime, console, workflow, evidence, ledger,
  report, validation, route, operator, status.
- Link major claims to the file that supports them.
- Separate production-capable workflows from prototypes and research.
- Describe sensitive workflows as reviewed, gated, and operator-controlled.
- Keep module names when linking exact files, but translate their meaning in the
  surrounding sentence.
- Avoid unsupported claims about revenue, customers, market performance,
  regulatory standing, partner commitments, or grant eligibility.

## Suggested Replacements

| Avoid in current front-door docs | Use instead |
|---|---|
| "Aureon is alive" | "Aureon runs as a local operator runtime." |
| "Self-modifying system" | "Controlled code-generation and review support." |
| "Full autonomy" | "Operator-controlled automation with explicit gates." |
| "Guaranteed profit" | "Trading research and execution-support tooling." |
| "Live now" | "Current local capability" or "available in this repository." |
| "Unstoppable" | "Locally reproducible" or "auditable." |
| "Cartel exposure" | "Market-structure research." |
| "Spiritual warfare" | "Historical or theoretical research archive." |
| "Liberation protocol" | "Research or operations workflow." |

## Archive Handling

Historical terms may remain inside archived documents when preserving project
history. New front-facing docs should translate them into the preferred terms
above and link to the archive when historical context is useful.
