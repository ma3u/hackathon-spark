---
type: index
title: Decisions
description: Pointer into the Architecture Decision Records.
timestamp: 2026-06-14
tags: [decisions, adr, index]
---

# Decisions

Architecturally significant decisions are recorded as **ADRs** (Nygard-style, immutable) in
[`../../adr/`](../../adr/index.md). The OKF concepts above cross-link the ADR(s) that govern
them.

| ADR | Title | Governs concept(s) |
| --- | ----- | ------------------ |
| [0002](../../adr/0002-graphrag-over-vector-rag.md) | GraphRAG over vector-RAG | [[neo4j-loader-graphrag]], [[neo4j]] |
| [0003](../../adr/0003-spark-graph-format-contract.md) | SPARK graph format contract | [[spark-graph-format]], [[graph-build]] |
| [0004](../../adr/0004-dual-path-stdlib-demo.md) | Dual-path + stdlib demo | all services; [[demo-dep-free]] |
| [0005](../../adr/0005-audio-second-provenance.md) | Audio-second provenance | [[provenienz-belegt-durch]], [[transkriptsegment]] |
| [0006](../../adr/0006-factcheck-always-has-source.md) | FactCheck always has a Quelle | [[faktencheck-quelle]], [[factcheck]] |
| [0007](../../adr/0007-llm-verdicts-real-persons-disclaimer.md) | Real-person verdicts + disclaimer | [[factcheck]] |
| [0008](../../adr/0008-two-graphs-per-session-namespaces.md) | Two graphs per session | [[bundestag-opendata-xml]], [[youtube-mediathek]] |
| [0009](../../adr/0009-parameterized-cypher-safe-gating.md) | Parameterized Cypher + `_SAFE` | [[neo4j-loader-graphrag]] |
| [0010](../../adr/0010-on-prem-llm-openai-compatible.md) | On-prem LLM endpoint | [[azure-ai-foundry]] |
| [0011](../../adr/0011-eupl-public-money-public-code.md) | EUPL-1.2 / PMPC | licensing |
| [0012](../../adr/0012-five-layer-ontology-schicht.md) | 5-layer ontology | [[ontologie-5-schichten]] |
