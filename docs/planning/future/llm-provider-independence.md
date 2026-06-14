---
title: LLM provider independence — migrate call sites + self-host options
status: future
owner: ma3u
updated: 2026-06-14
adr: ["0015", "0010", "0014"]
knowledge: ["docs/knowledge/apis/azure-ai-foundry.md"]
---

# LLM provider independence — migrate call sites + self-host options

Boundary + swap-safety landed (ADR-0015). Remaining work to make the provider fully a config.

**Source:** ADR-0015.

## Done (2026-06-14)
- [x] `pipeline/llm.py` — generic OpenAI-compatible boundary (`LLM_*` env overrides Azure).
- [x] `scripts/llm_provider_eval.py` — provider eval (chat-JSON · Text2Cypher · embed-dim);
      verified against Azure.
- [x] Embedding swap-safety — `embedding_model` tag + `vector_search.py --reembed`.
- [x] `.env.example` provider presets (Azure/Ollama/vLLM/OpenRouter/LiteLLM).

## Open
- [ ] **Migrate call sites** to `pipeline.llm` (non-breaking): `factcheck.py`,
      `session_ingest.py`, `neo4j_graphrag.py`, `scripts/haystack_neo4j.py`,
      `scripts/vector_search.py` — so there is exactly one provider boundary.
- [ ] **Self-hostable embedder** path (bge-m3 / multilingual-e5) for full on-prem; document the
      **index-recreate** step when the embedding dimension changes.
- [ ] **LiteLLM gateway** in front of `pipeline.llm` for runtime fallback/routing (ADR-0014).
- [ ] Smoke the eval against a **second** provider (e.g. local Ollama) to prove the swap.
