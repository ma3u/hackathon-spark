---
type: api
title: Azure AI Foundry (LLM + embeddings)
description: OpenAI-compatible LLM + embedding endpoint used for extraction, fact-check, Text2Cypher.
resource: scripts/graphrag_compare.py
tags: [api, llm, azure, embeddings, openai-compatible, on-prem]
timestamp: 2026-06-14
---

# Azure AI Foundry (LLM + embeddings)

LLM access via an **OpenAI-compatible** endpoint (`.env`, never committed). On-prem deployments
point the same config at Ollama / vLLM (ADR-0010).

- **Models:** `Mistral-Large-3` (fast, ~2–4 s) and `Kimi-K2.6` (reasoning, slower, needs more
  `max_tokens`) — compared in `scripts/graphrag_compare.py`.
- **Embeddings:** `text-embedding-3-large` (3072-d, multilingual) → native Neo4j vector index
  (`scripts/vector_search.py`); Mistral-Embed not in the Azure catalog.
- Used for: extraction, fact-check NLI, Text2Cypher synthesis, Haystack generator.

**Source:** `README.md:311-340`; `docs/neo4j-echtsitzungen.md`; `.env.example`. ADR-0010.
