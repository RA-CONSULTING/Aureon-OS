# Aureon Ollama Cognitive Bridge

- status: ollama_cognitive_bridge_ready
- generated_at: 2026-05-22T07:21:40.504692+00:00
- ollama_reachable: True
- resolved_model: llama3:latest
- hnc_auris_ready: True
- metacognitive_ready: True
- hand_in_hand_ready: True

## Crew
- Phi Chat Steward: Accept the human message, redact context, and keep the dashboard conversation live.
- Aureon Metacognitive Context Builder: Gather HNC/Auris, cognitive, voice, role, and skill evidence before the model answers.
- Ollama Language Worker: Generate local language responses through the installed Ollama model when reachable.
- Aureon Brain Fallback: Keep reasoning available when the local model is offline, slow, or blocked by audit mode.
- HNC/Auris Drift Inspector: Hold claims when harmonic, node, or cognitive proof is missing or stale.
- ThoughtBus Evidence Clerk: Publish chat and bridge status evidence without leaking secrets.

## Proof Checklist
- pass: Ollama server is reachable on the local machine (http://localhost:11434)
- pass: Ollama model library is visible (qwen2.5:0.5b, llama3:latest)
- pass: A chat model is resolved for Aureon (llama3:latest)
- pass: HNC/Auris context is ready for guarded conversation (sources=6)
- pass: Aureon metacognitive evidence is present (sources=6)
- pass: Agent roles can declare who, what, where, when, how, and act (agent company / creative guardian)
- pass: Aureon Brain fallback is declared when Ollama is unavailable (AureonHybridAdapter falls back to AureonBrainAdapter)
- pass: Existing live-action and credential gates remain authoritative (no bypass introduced)

## Next Actions
- use_hybrid_backend: Use the hand-in-hand voice backend for the dashboard chat lane.
