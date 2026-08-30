"""
Aureon ↔ Ollama Integration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Native Ollama client (http://localhost:11434/api/*) plus an LLMAdapter
shim so OllamaBridge is a drop-in replacement for AureonLocalAdapter
inside the in-house AI stack.

The existing AureonLocalAdapter already spoke to Ollama via its
OpenAI-compatible /v1 surface. This module adds:

  • First-class access to Ollama's NATIVE API (/api/chat, /api/generate,
    /api/embed, /api/tags, /api/show, /api/pull, /api/ps, /api/version)
    so the vault can pull models, watch running models, and generate
    embeddings without pretending to be OpenAI.
  • A small OllamaLLMAdapter that routes vault-voice prompts through
    /api/chat directly, honoring Ollama-specific options (keep_alive,
    think mode, format=json).
"""

from aureon.integrations.ollama.hnc_phi_swarm import (
    HNCPhiOllamaSwarm,
    build_phi_swarm_plan,
)
from aureon.integrations.ollama.model_switchboard import (
    HNC_ROUTE_SCHEMA,
    LANES,
    HNCModelRoutingReceipt,
    OllamaModelSelection,
    OllamaModelSwitchboard,
    validate_hnc_model_routing_receipt,
)
from aureon.integrations.ollama.ollama_adapter import OllamaLLMAdapter
from aureon.integrations.ollama.ollama_bridge import (
    OllamaBridge,
    OllamaBridgeError,
    OllamaModel,
    OllamaPsEntry,
)
from aureon.ollama_config import (
    ensure_ollama_runtime_config,
    is_ollama_cloud_url,
    ollama_authorization_headers,
    ollama_config_snapshot,
    resolve_external_llm_fallback,
    resolve_ollama_api_key,
    resolve_ollama_native_base_url,
    resolve_ollama_openai_base_url,
    resolve_ollama_reasoning_effort,
)

__all__ = [
    "OllamaBridge",
    "OllamaModel",
    "OllamaPsEntry",
    "OllamaBridgeError",
    "OllamaLLMAdapter",
    "LANES",
    "HNC_ROUTE_SCHEMA",
    "HNCModelRoutingReceipt",
    "OllamaModelSelection",
    "OllamaModelSwitchboard",
    "validate_hnc_model_routing_receipt",
    "HNCPhiOllamaSwarm",
    "build_phi_swarm_plan",
    "ensure_ollama_runtime_config",
    "is_ollama_cloud_url",
    "ollama_authorization_headers",
    "ollama_config_snapshot",
    "resolve_external_llm_fallback",
    "resolve_ollama_api_key",
    "resolve_ollama_native_base_url",
    "resolve_ollama_openai_base_url",
    "resolve_ollama_reasoning_effort",
]
