"""
Aureon Operator — LLM provider catalog.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The single source of truth for *which* providers Aureon can dial and *how* — the
metadata behind the Providers settings UI and the ``/api/providers`` surface.

Each entry maps a provider to the environment variables the switchboard reads
(``providers.py`` / ``config.py``), a sensible default endpoint + model, and the
links a user needs to fetch their own key. **No secrets live here** — only
configuration shape. Keys are entered in the UI and kept in the encrypted
keystore (``keystore.py``); this module just says where they belong.

The five newcomers (DeepSeek, Mistral, Groq, OpenRouter, Perplexity) are all
OpenAI-compatible, so they ride the ``openai_compat`` kind — one adapter path,
each with its own key/base-URL env.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ProviderInfo:
    """Static description of one dialable LLM provider."""

    id: str                       # stable slug for the UI + keystore
    label: str                    # human name for the UI
    kind: str                     # openai | grok | gemini | anthropic | local | openai_compat
    key_env: str                  # env var holding the API key ("" for keyless local)
    default_model: str
    get_keys_url: str             # where a user creates a key
    docs_url: str
    base_url_env: str = ""        # env var for the endpoint ("" when the SDK fixes it, e.g. Anthropic)
    default_base_url: str = ""     # shown/prefilled in the UI (blank = adapter default)
    key_optional: bool = False    # local Ollama needs no key
    notes: str = ""
    spec_name: str = ""           # ModelSpec.name in the registry (defaults to id)

    @property
    def registry_name(self) -> str:
        return self.spec_name or self.id

    def to_public_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "key_env": self.key_env,
            "base_url_env": self.base_url_env,
            "default_base_url": self.default_base_url,
            "default_model": self.default_model,
            "get_keys_url": self.get_keys_url,
            "docs_url": self.docs_url,
            "key_optional": self.key_optional,
            "notes": self.notes,
            "registry_name": self.registry_name,
        }


# The catalog. Order is the display order in the UI.
CATALOG: List[ProviderInfo] = [
    ProviderInfo(
        id="openai", label="OpenAI (ChatGPT)", kind="openai",
        key_env="OPENAI_API_KEY", base_url_env="OPENAI_BASE_URL",
        default_base_url="https://api.openai.com/v1", default_model="gpt-4o-mini",
        get_keys_url="https://platform.openai.com/api-keys",
        docs_url="https://platform.openai.com/docs/api-reference",
    ),
    ProviderInfo(
        id="anthropic", label="Anthropic (Claude)", kind="anthropic",
        key_env="ANTHROPIC_API_KEY", base_url_env="",
        default_base_url="", default_model="claude-3-5-sonnet-latest",
        get_keys_url="https://console.anthropic.com/settings/keys",
        docs_url="https://docs.anthropic.com/en/api/getting-started",
    ),
    ProviderInfo(
        id="grok", label="xAI (Grok)", kind="grok",
        key_env="XAI_API_KEY", base_url_env="XAI_BASE_URL",
        default_base_url="https://api.x.ai/v1", default_model="grok-2-latest",
        get_keys_url="https://console.x.ai", docs_url="https://docs.x.ai",
    ),
    ProviderInfo(
        id="gemini", label="Google (Gemini)", kind="gemini",
        key_env="GEMINI_API_KEY", base_url_env="GEMINI_BASE_URL",
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model="gemini-1.5-flash",
        get_keys_url="https://aistudio.google.com/apikey",
        docs_url="https://ai.google.dev/gemini-api/docs",
    ),
    ProviderInfo(
        id="ollama", label="Ollama (local or cloud)", kind="local",
        key_env="AUREON_LLM_API_KEY", base_url_env="AUREON_LLM_BASE_URL",
        default_base_url="http://localhost:11434/v1", default_model="llama3.1",
        get_keys_url="https://ollama.com/settings/keys",
        docs_url="https://docs.ollama.com/cloud", key_optional=True, spec_name="local",
        notes="Leave the key blank for local Ollama; for Ollama Cloud set "
              "base URL https://ollama.com/v1 and paste a cloud API key.",
    ),
    ProviderInfo(
        id="deepseek", label="DeepSeek", kind="openai_compat",
        key_env="DEEPSEEK_API_KEY", base_url_env="DEEPSEEK_BASE_URL",
        default_base_url="https://api.deepseek.com/v1", default_model="deepseek-chat",
        get_keys_url="https://platform.deepseek.com/api_keys",
        docs_url="https://api-docs.deepseek.com",
    ),
    ProviderInfo(
        id="mistral", label="Mistral", kind="openai_compat",
        key_env="MISTRAL_API_KEY", base_url_env="MISTRAL_BASE_URL",
        default_base_url="https://api.mistral.ai/v1", default_model="mistral-large-latest",
        get_keys_url="https://console.mistral.ai/api-keys",
        docs_url="https://docs.mistral.ai/api",
    ),
    ProviderInfo(
        id="groq", label="Groq", kind="openai_compat",
        key_env="GROQ_API_KEY", base_url_env="GROQ_BASE_URL",
        default_base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        get_keys_url="https://console.groq.com/keys",
        docs_url="https://console.groq.com/docs/openai",
    ),
    ProviderInfo(
        id="openrouter", label="OpenRouter", kind="openai_compat",
        key_env="OPENROUTER_API_KEY", base_url_env="OPENROUTER_BASE_URL",
        default_base_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-4o-mini",
        get_keys_url="https://openrouter.ai/keys",
        docs_url="https://openrouter.ai/docs",
        notes="One key, many models — set the model as vendor/model (e.g. anthropic/claude-3.5-sonnet).",
    ),
    ProviderInfo(
        id="perplexity", label="Perplexity", kind="openai_compat",
        key_env="PERPLEXITY_API_KEY", base_url_env="PERPLEXITY_BASE_URL",
        default_base_url="https://api.perplexity.ai", default_model="sonar",
        get_keys_url="https://www.perplexity.ai/settings/api",
        docs_url="https://docs.perplexity.ai",
    ),
]

_BY_ID: Dict[str, ProviderInfo] = {p.id: p for p in CATALOG}


def get_provider(provider_id: str) -> ProviderInfo | None:
    return _BY_ID.get(provider_id)


def provider_ids() -> List[str]:
    return [p.id for p in CATALOG]


# The env vars every catalog provider owns — used to scrub/mask and to know what
# the keystore is allowed to write.
def managed_env_vars() -> List[str]:
    out: List[str] = []
    for p in CATALOG:
        if p.key_env:
            out.append(p.key_env)
        if p.base_url_env:
            out.append(p.base_url_env)
    return out


__all__ = ["ProviderInfo", "CATALOG", "get_provider", "provider_ids", "managed_env_vars"]
