# 0014. SPARK reuse: Temporal + LiteLLM gateway; keep Haystack; no Docling/MinIO for Challenge 2

- **Status:** Accepted
- **Date:** 2026-06-14
- **Deciders:** maintainer (ma3u)
- **Source(s):** `docs/spark-und-echtdaten.md §A-B`; SPARK README (gitlab.opencode.de/bmds/…/
  spark-workflow, fetched 2026-06-14); `scripts/haystack_neo4j.py`; `README.md` GenAI section

## Context

SPARK Workflow (BMDS) and `graph-protokoll` share mission/licence/on-prem-LLM pattern but no
code. SPARK's stack: Python/FastAPI · **Temporal** · Postgres · **MinIO/S3** · Elasticsearch ·
**Qdrant** (vector-RAG) · **Docling** (PDF/DOCX) · **LiteLLM/vLLM** — and **no graph**. The
question was which SPARK pieces to reuse without diluting our graph-first design. An initial
list over-reached (it included Docling + MinIO); this ADR records the trimmed, deliberate scope.

## Decision

**Reuse:**
- **Temporal** for the *production* path only — durable retries/checkpoints for long, flaky,
  resumable jobs (bulk captions + LLM fact-check over the 56 YouTube sessions; mass Neo4j
  loads). Wrap `session_ingest.*` / `sync_sessions` activities; the **stdlib demo stays
  dep-free** (ADR-0004).
- **LiteLLM** as a thin **gateway**, *when* LLM-call management hurts: multi-provider routing
  (Azure Mistral + Kimi + Ollama/vLLM), fallback, rate-limit/cost control. Sits beneath our
  existing `openai`-SDK calls (`base_url`); not adopted now (one Azure resource at hackathon
  scale = direct SDK is fine).

**Keep (already ours):**
- **Haystack** remains one of three retrieval modalities (`scripts/haystack_neo4j.py`:
  full-text RAG), alongside **GraphRAG/Text2Cypher (primary)** and **vector**. LiteLLM and
  Haystack are complementary layers (gateway vs. RAG framework), not alternatives — a Haystack
  generator may call models *through* LiteLLM.

**Do NOT adopt for Challenge 2:**
- **Docling** — our inputs are amtliches **XML** + audio/ASR + YouTube captions; no PDF/DOCX in
  the core path. Only revisit if PDF Drucksachen/committee papers ever become a full-text front.
- **MinIO** — no object-storage need (graphs are small JSON in git/Neo4j; audio/video are
  **deeplinked**, not stored). Also: the OSS MinIO server had its admin console/UI removed in
  2025 and the community edition is widely seen as neglected — a poor fit for Public-Money-
  Public-Code. If object storage is ever needed: filesystem, Ceph/RADOS, SeaweedFS, Garage, or
  cloud S3.

## Consequences

- Production hardening path is clear (Temporal + optional LiteLLM) without touching the dep-free
  demo or the graph-first architecture.
- We avoid two dependencies (Docling, MinIO) that add weight without serving Challenge 2.
- Adoption is staged/opt-in; today nothing changes operationally (tracked in
  `docs/planning/future/spark-reuse-temporal-litellm.md`).

## Alternatives considered

- **Adopt SPARK's full stack** — rejected: pulls in Qdrant-as-primary, Docling, MinIO, and a
  Temporal cluster requirement; dilutes the graph-first design and breaks the zero-dep demo.
- **LiteLLM now** — deferred: no current pain with the direct `openai` SDK against one Azure
  resource.
- **Replace Haystack with LiteLLM** — rejected: category error (RAG framework vs. gateway).
- **Keep MinIO/Docling "just in case"** — rejected: YAGNI + MinIO OSS maintenance risk.
