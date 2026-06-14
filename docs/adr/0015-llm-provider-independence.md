# 0015. LLM provider independence

- **Status:** Accepted (boundary implemented 2026-06-14)
- **Date:** 2026-06-14
- **Deciders:** maintainer (ma3u)
- **Source(s):** `pipeline/llm.py`; `scripts/llm_provider_eval.py`; `scripts/vector_search.py`
  (`reembed_stale`, `--reembed`); `.env.example`; ADR-0010 (on-prem endpoint), ADR-0002
  (GraphRAG primary)

## Context

The project must not be locked to one LLM vendor (cost, availability, DSGVO/data sovereignty,
PMPC). Calls already went through an OpenAI-compatible `base_url`, but per call site with
Azure-specific env names, and embeddings were silently bound to one model/dimension — a hidden
lock-in (stored vectors are model-specific).

## Decision

1. **Single OpenAI-compatible boundary.** All LLM/embedding access goes through `pipeline/llm.py`
   (`config()`, `chat()`, `embed()`, `chat_client()`), reading **generic** env
   (`LLM_BASE_URL`/`LLM_API_KEY`/`LLM_CHAT_MODEL`/`LLM_PROVIDER`) that **overrides** the
   Azure-specific names (backward compatible — Azure stays the default). The provider is a
   **configuration**, not a code dependency: Azure AI Foundry · Ollama · vLLM · OpenRouter ·
   LiteLLM-gateway · LocalAI (presets in `.env.example`).
2. **Portable subset only.** Use just `chat.completions` + `embeddings`. No vendor-proprietary
   tool-call/structured-output formats or non-exportable fine-tunes. Validate outputs (verdikt ∈
   `VERDIKTE`, `assert quelle`) so a weaker model degrades gracefully.
3. **On-prem fallback is first-class** (ADR-0010): Ollama/vLLM with open-weight models → never
   hard-bound to a cloud vendor.
4. **GraphRAG stays primary** (ADR-0002): Text2Cypher needs no embeddings, so the system answers
   even with **no embedding provider**; vector is complementary.
5. **Embeddings are swap-safe.** Each `Transkriptsegment.embedding` records `embedding_model`;
   `vector_search.py --reembed` discards vectors of a different model and recomputes. A
   dimension change additionally requires recreating the vector index. Prefer a self-hostable
   multilingual embedder (bge-m3 / multilingual-e5) when leaving the cloud.
6. **Eval before swap.** `scripts/llm_provider_eval.py` checks the configured provider over the
   portable subset (chat-JSON verdict · Text2Cypher · embedding dim + latency) → evidence-based
   switch, not faith.

## Consequences

- Switching provider = edit `.env` (+ re-embed if the embedder changes), no code change.
- One place (`pipeline/llm.py`) to later insert a LiteLLM gateway / fallback (ADR-0014).
- Existing call sites (`factcheck.py`, `session_ingest.py`, `neo4j_graphrag.py`,
  `haystack_neo4j.py`) already take `base_url`/`api_key` params; migrating them to `pipeline/llm`
  is follow-up (`future/llm-provider-independence.md`), non-breaking.
- The dep-free demo stays LLM-free → inherently provider-independent.

## Alternatives considered

- **Provider-specific SDK (AzureOpenAI/Anthropic/…)** — rejected: lock-in, breaks on-prem.
- **Ignore embedding lock-in** — rejected: silent re-embedding cost on any swap; now explicit.
- **Drop vector search to avoid embedding lock-in entirely** — rejected: vector is a valuable
  complementary path; GraphRAG-primary already makes it optional, swap-safety handles the rest.
