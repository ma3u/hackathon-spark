"""
Zentrale, anbieter-agnostische LLM-Grenze (Provider-Unabhängigkeit, ADR-0015).

Alle LLM-/Embedding-Zugänge laufen über EINEN OpenAI-kompatiblen Endpoint (`base_url` +
`api_key` + Modellname aus `.env`). So ist der Anbieter eine **Konfiguration** — Azure AI
Foundry, Ollama, vLLM, OpenRouter, ein LiteLLM-Gateway oder LocalAI — und keine
Code-Abhängigkeit. Es wird NUR der **portable Teilumfang** genutzt: `chat.completions` +
`embeddings`. Keine anbieter-proprietären Features (proprietäre Tool-Call-/Structured-Output-
Formate, nicht-exportierbare Fine-Tunes).

Generische Variablen `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_CHAT_MODEL` / `LLM_PROVIDER`
überschreiben die Azure-spezifischen (`AZURE_AI_ENDPOINT` / `AZURE_AI_API_KEY` /
`MISTRAL_DEPLOYMENT`) — Rückwärtskompatibel: ohne sie gilt weiter Azure.

Produktivpfad: echter LLM über den konfigurierten Endpoint (`openai`-SDK, lazy importiert).
Demopfad: hier keiner nötig — der dep-freie Demo (`run_demo.py`) ruft GAR KEIN LLM
(regelbasiert) und ist damit per se anbieterfrei.

Hinweis Embeddings: Vektoren sind **modell-/dimensionsgebunden**. Ein Wechsel des
Embedding-Modells erfordert Neu-Embedding (`scripts/vector_search.py --reembed`); bei
abweichender Dimension zusätzlich den Vektor-Index neu anlegen.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_PROVIDER_HINTS = [("azure", "azure"), ("openrouter", "openrouter"), ("ollama", ":11434"),
                   ("vllm", "vllm"), ("litellm", ":4000"), ("localai", "localai")]


@dataclass
class LLMConfig:
    provider: str
    base_url: str
    api_key: str
    chat_model: str
    embed_model: str
    embed_dim: int


def _provider_from(base_url: str) -> str:
    b = (base_url or "").lower()
    for name, frag in _PROVIDER_HINTS:
        if frag in b:
            return name
    return "custom"


def config() -> LLMConfig:
    """LLM-Konfiguration aus der Umgebung — generisch, mit Azure-Fallback."""
    base = os.environ.get("LLM_BASE_URL") or os.environ.get("AZURE_AI_ENDPOINT", "")
    key = os.environ.get("LLM_API_KEY") or os.environ.get("AZURE_AI_API_KEY", "")
    if not base or not key:
        raise RuntimeError(
            "LLM-Endpoint fehlt: setze LLM_BASE_URL/LLM_API_KEY (oder AZURE_AI_ENDPOINT/"
            "AZURE_AI_API_KEY) in .env. Anbieter ist eine Konfiguration (ADR-0015).")
    return LLMConfig(
        provider=os.environ.get("LLM_PROVIDER") or _provider_from(base),
        base_url=base, api_key=key,
        chat_model=(os.environ.get("LLM_CHAT_MODEL")
                    or os.environ.get("MISTRAL_DEPLOYMENT", "Mistral-Large-3")),
        embed_model=os.environ.get("EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
        embed_dim=int(os.environ.get("EMBEDDING_DIM", "3072")),
    )


def chat_client(cfg: LLMConfig | None = None):
    """OpenAI-kompatibler Client für den konfigurierten Anbieter (lazy import)."""
    from openai import OpenAI  # lazy: nur Produktivpfad
    c = cfg or config()
    return OpenAI(base_url=c.base_url, api_key=c.api_key)


def chat(messages: list[dict], *, model: str | None = None, temperature: float = 0.3,
         max_tokens: int = 800, cfg: LLMConfig | None = None) -> str:
    """Eine Chat-Completion über den portablen Teilumfang. Gibt den Text zurück."""
    c = cfg or config()
    resp = chat_client(c).chat.completions.create(
        model=model or c.chat_model, temperature=temperature,
        max_tokens=max_tokens, messages=messages)
    return (resp.choices[0].message.content or "").strip()


def embed(texts, *, cfg: LLMConfig | None = None) -> list[list[float]]:
    """Embeddings über den portablen Teilumfang. Liste der Vektoren."""
    c = cfg or config()
    resp = chat_client(c).embeddings.create(model=c.embed_model, input=list(texts))
    return [d.embedding for d in resp.data]
