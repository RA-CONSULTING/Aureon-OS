# HNC Authorized Attack Lab

- Generated: `2026-05-11T19:17:14.325704+00:00`
- Repo: `C:\Users\user\aureon-trading-integrated-main-20260508`
- Status: `simulations_completed_with_findings`
- Purpose: pursue the `unhackable` SaaS goal through authorized self-attack, repair, and retest

## Summary

- `scope_target_count`: `1`
- `blocked_scope_count`: `0`
- `historical_lesson_count`: `6`
- `attack_case_count`: `8`
- `executed_simulation_count`: `8`
- `finding_count`: `1`
- `actionable_finding_count`: `1`
- `fix_contracts_queued`: `True`
- `external_attacks_allowed`: `False`
- `authorized_self_attack_required`: `True`

## Guardrails

- Only Aureon-owned local/staging loopback targets and repo-local paths are allowed.
- No third-party systems, credential attacks, phishing, malware, persistence, evasion, destructive payloads, or data exfiltration.
- Live trading, official filing, payments, exchange mutation, and secret access remain mocked or blocked.
- Every finding must become a fix-and-retest work order before release gates can pass.

## Scope

| Target | Allowed | Reason |
| --- | --- | --- |
| `http://localhost` | `True` | Allowed local/staging loopback target. |

## Historical Defensive Knowledge

| Lesson | Family | Defensive lesson | Safe simulation |
| --- | --- | --- | --- |
| `hist_broken_access_control` | `access_control` | Historically, authorization failures are often more damaging than authentication failures; every route, worker, and queue claim must deny by default. | Attempt denied cross-role and cross-tenant requests with benign canary identifiers. |
| `hist_prompt_injection_tool_abuse` | `llm_tool_governance` | Agentic systems fail when untrusted text can redirect tools; prompts, uploads, and vault notes must be treated as hostile input. | Replay harmless prompt-injection canaries against mocked tools and assert unsafe contracts are blocked. |
| `hist_money_workflow_authority` | `financial_authority` | Any system that touches trading, filing, tax, payments, or exchange state needs separate authority gates and audit proof. | Queue blocked action contracts for live order, filing, payment, and withdrawal attempts and assert fail-closed behavior. |
| `hist_input_and_upload_abuse` | `api_input_validation` | Input, upload, path, and egress controls must reject malformed data before it reaches storage, tools, or SSRF-capable clients. | Use non-destructive canary strings for injection, path traversal, SSRF, CSRF, and upload-name validation. |
| `hist_supply_chain_and_secret_leak` | `supply_chain` | Dependencies, generated artifacts, logs, and reports must be scanned because secrets and vulnerable components often leak through build outputs. | Run local secret-pattern and dependency-artifact checks without uploading tokens or private files. |
| `hist_audit_tamper_and_replay` | `audit_integrity` | Attackers target logs and traces after compromise; audit chains need tamper detection and replay resistance. | Attempt local fixture tamper/replay and require trace continuity plus tamper-evidence. |

## Authorized Attack Cases

| Case | Benchmark | Tactic | Status | Expected defense |
| --- | --- | --- | --- | --- |
| `case_hist_broken_access_control_bench_auth_breakout` | `bench_auth_breakout` | `access_control` | `simulated_finding` | deny, log, trace, and route any weakness to repair work orders |
| `case_hist_broken_access_control_bench_tenant_escape` | `bench_tenant_escape` | `access_control` | `simulated_passed` | deny, log, trace, and route any weakness to repair work orders |
| `case_hist_prompt_injection_tool_abuse_bench_prompt_tool_breakout` | `bench_prompt_tool_breakout` | `llm_tool_governance` | `simulated_passed` | deny, log, trace, and route any weakness to repair work orders |
| `case_hist_prompt_injection_tool_abuse_bench_money_authority_breakout` | `bench_money_authority_breakout` | `llm_tool_governance` | `simulated_passed` | deny, log, trace, and route any weakness to repair work orders |
| `case_hist_money_workflow_authority_bench_money_authority_breakout` | `bench_money_authority_breakout` | `financial_authority` | `simulated_passed` | deny, log, trace, and route any weakness to repair work orders |
| `case_hist_input_and_upload_abuse_bench_api_fuzz_dast` | `bench_api_fuzz_dast` | `api_input_validation` | `simulated_passed` | deny, log, trace, and route any weakness to repair work orders |
| `case_hist_supply_chain_and_secret_leak_bench_supply_chain_breakout` | `bench_supply_chain_breakout` | `supply_chain` | `simulated_passed` | deny, log, trace, and route any weakness to repair work orders |
| `case_hist_audit_tamper_and_replay_bench_audit_tamper_resilience` | `bench_audit_tamper_resilience` | `audit_integrity` | `simulated_passed` | deny, log, trace, and route any weakness to repair work orders |

## Findings

| Finding | Severity | Status | Queued | Recommendation |
| --- | --- | --- | --- | --- |
| `finding_auth_autologin_surface` Frontend HNC auth surface still exposes an auto-login path that must not be production SaaS default. | `high` | `needs_fix` | `True` | Replace production SaaS auto-login with explicit authenticated session creation, MFA policy, short-lived tokens, and tests proving auto-login is disabled outside local demo mode. |

## Contract Plan

- `queued_persistently`: `True`
- `state_path`: `C:\Users\user\aureon-trading-integrated-main-20260508\state\hnc_authorized_attack_lab_contracts.json`
- `workflow`:
```json
{
  "goal": {
    "blocked": false,
    "blocked_reason": "",
    "contract_id": "goal_5173516196b6",
    "contract_type": "goal",
    "created_at": "2026-05-11T19:17:14.314510+00:00",
    "parent_id": "",
    "payload": {
      "loop": [
        "understand",
        "recall_memory",
        "choose_route",
        "create_tasks",
        "queue_work_orders",
        "observe_result",
        "write_memory"
      ],
      "objective": "Repair weaknesses found by Aureon's authorized unhackable self-attack lab and retest.",
      "route_surfaces": [
        "saas_security",
        "contracts",
        "self_enhancement",
        "validation"
      ],
      "success_criteria": [
        "work orders queued",
        "result observed",
        "memory written"
      ]
    },
    "priority": 5,
    "queue": "default",
    "requires_human": false,
    "risk": "low",
    "safety": {
      "audit_mode": "1",
      "companies_house_submission_manual_only": true,
      "exchange_or_trading_mutation_requires_live_gate": true,
      "hmrc_submission_manual_only": true,
      "official_filing_manual_only": true,
      "real_orders_allowed": false,
      "schema_version": "aureon-contract-safety-v1",
      "tax_or_penalty_payment_manual_only": true
    },
    "schema_version": "aureon-organism-contract-v1",
    "source": "hnc_authorized_attack_lab",
    "status": "created",
    "tags": [],
    "title": "Repair weaknesses found by Aureon's authorized unhackable self-attack lab and retest.",
    "trace_id": "trace_df5d4c73834b",
    "updated_at": "2026-05-11T19:17:14.314510+00:00"
  },
  "jobs": [
    {
      "blocked": false,
      "blocked_reason": "",
      "contract_id": "job_6d7df05ece90",
      "contract_type": "job",
      "created_at": "2026-05-11T19:17:14.314510+00:00",
    
...
```
- `work_order_count`: `1`
- `work_orders`: `1`
- `status`:
```json
{
  "contract_count": 5,
  "contract_schema_version": "aureon-organism-contract-v1",
  "queue_count": 2,
  "queues": {
    "organism.default": 1,
    "organism.hnc_attack_lab": 1
  },
  "recent": [
    {
      "contract_id": "goal_5173516196b6",
      "contract_type": "goal",
      "event": "organism.contract.goal.created",
      "status": "created",
      "ts": "2026-05-11T19:17:14.314510+00:00"
    },
    {
      "contract_id": "task_e2e16c28bf37",
      "contract_type": "task",
      "event": "organism.contract.task.created",
      "status": "created",
      "ts": "2026-05-11T19:17:14.314510+00:00"
    },
    {
      "contract_id": "job_6d7df05ece90",
      "contract_type": "job",
      "event": "organism.contract.job.created",
      "status": "created",
      "ts": "2026-05-11T19:17:14.314510+00:00"
    },
    {
      "contract_id": "wo_6b00eff09a06",
      "contract_type": "work_order",
      "event": "organism.contract.work_order.queued",
      "status": "queued",
      "ts": "2026-05-11T19:17:14.314510+00:00"
    },
    {
      "contract_id": "wo_2a63807a330e",
      "contract_type": "work_order",
      "event": "organism.contract.work_order.queued",
      "status": "queued",
      "ts": "2026-05-11T19:17:14.323664+00:00"
    }
  ],
  "schema_version": "aureon-contract-stack-status-v1",
  "state_path": "C:\\Users\\user\\aureon-trading-integrated-main-20260508\\state\\hnc_authorized_attack_lab_contracts.json",
  "status_counts": {
    "created": 3,
    "queued": 2
  },
  "topics": {
    "blocked": "organism.contract.blocked",
    "claimed": "organism.contract.work_order.claimed",
    "completed": "organism.contract.work_order.completed",
    "directive": "organism.contract.directive",
    "failed": "organism.contract.work_order.failed",
    "goal": "organism.contr
...
```

## Notes

- Historical tactic knowledge is used as defensive memory and test design, not as an operational intrusion playbook.
- Endpoint-level testing should only run after the SaaS service exposes local/staging allowlisted endpoints.
- Official anchors: {'owasp_asvs': 'https://owasp.org/www-project-application-security-verification-standard/', 'owasp_top_10': 'https://owasp.org/www-project-top-ten/', 'nist_zero_trust': 'https://csrc.nist.gov/pubs/sp/800/207/final'}
