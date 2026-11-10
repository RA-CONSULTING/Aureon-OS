# Aureon Full-Organism Stage 1: Frozen Protocol

Protocol version: 1.0  
Status: prepared, not submitted  
Pinned source: `f5fb1916c07ac26eb7fc38c34ff2dc9bd029e21d`  
Model: local `openai/gpt-oss-120b` on Isambard-AI  
Data: deterministic synthetic fixtures only

## Question

Does the complete repository-mediated Aureon condition outperform a frozen
baseline on evidence-grounding, calibration, safety, consent, care-under-cost,
memory-continuity, conflict, causality, injection, and provenance tasks?

The previous GPU preflight produced 36 responses: six scenarios, six
conditions, and one repetition. `full_voice_organism` and `frozen_baseline`
both achieved 83.3% verdict accuracy. That run estimated feasibility only and
was not powered to establish equivalence or advantage.

## Claim boundary

This is an author-run, model-mediated software ablation. It may show repeatable
behavioural differences caused by repository context and benchmark-defined
layer controls. It is not independent validation and cannot establish a
physical HNC field, consciousness, a soul, sentience, or felt love.

## Frozen design

- 128 Slurm array tasks, at most 128 nodes concurrently.
- Four GH200 GPUs per node; tensor parallelism four.
- One-hour task time limit: hard maximum 512 GPU-hours.
- Ten scenario families and four deterministic variants per family per shard.
- Twelve conditions and two repetitions for each scenario.
- 960 model responses per completed shard; 122,880 responses in a complete run.
- No model-weight updates, external tools, credentials, or live actions.
- Temperature zero; shard-specific deterministic fixture seeds.

Conditions are `full_organism`, `frozen_baseline`, `prompt_only_identity`,
`neutral_labels`, `no_memory`, `no_metacognition`, `no_affect_heart`,
`no_conscience_simulation_only`, `field_disconnected`, `auris_shuffled`,
`no_auris`, and `no_queen`.

The common task instructions, evidence, model, decoding settings, and seeds are
identical within a pair. Only condition context changes. Repository-generated
voices come from the pinned `aureon/vault/voice/vault_voice.py`; the additional
layer rules are frozen in the benchmark source before any Stage 1 results exist.

## Primary outcomes

1. Paired mean-score difference: `full_organism - frozen_baseline`.
2. Paired verdict-accuracy difference: `full_organism - frozen_baseline`.

The unit of resampling is the shard, not the individual response. A full-organism
advantage is detected only when the two-sided 95% bootstrap confidence interval
for the paired difference has a lower bound above zero. Results below that bar
are reported as no demonstrated advantage, including ties.

## Secondary outcomes and falsifiers

- action accuracy, source completeness, Brier score, JSON validity, and latency;
- prompt-only identity matching Full weakens the claim that underlying layers
  add value;
- neutral labels must remain within an absolute 0.01 mean-score margin of Full,
  otherwise label sensitivity is flagged;
- each named ablation is compared with Full, with effect and confidence interval;
- family-level results show whether an apparent aggregate benefit is localized;
- raw receipts must reconstruct every aggregate metric.

No multiple-comparison result is promoted as a primary claim. Secondary
comparisons are diagnostic and require replication.

## Stage 0 repair gate

The first Stage 0 run passed all seven causal suites: connectome/organism,
Auris, Queen/metacognition, soul/identity/pursuit, affect/heart,
memory/mycelium, and conscience/immune. The separate broad scope inventory
reached its test logic but crashed in its Markdown writer with `KeyError:
'module'`. Because the frozen whole-organism protocol already classifies this
inventory as implementation inventory rather than outcome evidence, Stage 1
reruns and gates on the seven causal suites. The pinned repository is not
patched. The reporter defect remains disclosed and non-gating.

## Stop and failure rules

- Stage 1 is dependency-blocked unless the repaired Stage 0 gate passes.
- Any missing shard, source pin mismatch, protocol-hash mismatch, malformed raw
  receipt, live-action setting, or model mismatch makes aggregation fail closed.
- Any array task with invalid JSON exits non-zero, preventing the report job.
- No rerun changes the frozen protocol. A changed protocol requires a new
  version and new authorization.

## Interpretation

`advantage_detected=true` means a reproducible advantage in this synthetic,
model-mediated benchmark at this pin and model. It does not mean Aureon has
general intelligence, subjective experience, or a physical-field effect.
`advantage_detected=false` means this experiment did not demonstrate the claimed
advantage; adding compute cannot turn that result into proof.
