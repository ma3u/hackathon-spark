---
title: SPARK reuse — Temporal durability + optional LiteLLM gateway
status: future
owner: ma3u
updated: 2026-06-14
adr: ["0014"]
knowledge: ["docs/knowledge/apis/azure-ai-foundry.md"]
---

# SPARK reuse — Temporal durability + optional LiteLLM gateway

Harden the **production** path with SPARK's proven plumbing, per ADR-0014 — without touching the
dep-free demo (ADR-0004) or the graph-first design.

**Source:** ADR-0014; `docs/spark-und-echtdaten.md`.

## Scope

- [ ] **Temporal** — wrap the long/flaky/resumable jobs as durable activities: bulk YouTube
      captions + LLM fact-check (the 56 sessions), mass Neo4j loads, `sync_sessions`. Keep
      `run_demo.py` / `ingest_bundestag.py` stdlib + synchronous.
- [ ] **LiteLLM gateway** — only when LLM-call management hurts: route Azure Mistral/Kimi +
      Ollama/vLLM behind one base_url; add fallback, rate-limit, cost tracking. Drop-in under
      the existing `openai`-SDK calls (`factcheck`, `neo4j_graphrag`, `haystack_neo4j`).
- [ ] Align module naming with SPARK (Inhaltsextraktion / Vollständigkeits-/Plausibilitätsprüfung)
      for a clean Baukasten merge.

## Explicitly out of scope (ADR-0014)

- **Docling** (no PDF/DOCX in the Challenge-2 path) and **MinIO** (no object-storage need; OSS
  console removed 2025 / neglected → PMPC misfit). Haystack stays a retrieval modality, not
  replaced by LiteLLM.

## Trigger to start

Begins when the production bulk path (e.g. fact-checking all 56 YouTube sessions, or nightly
`sync_sessions`) needs durable retries or multi-provider LLM routing. Until then: not needed.
