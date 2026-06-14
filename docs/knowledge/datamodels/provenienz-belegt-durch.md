---
type: datamodel
title: Provenance (BELEGT_DURCH)
description: The audio-second proof backbone — every entity traceable to its source segment.
resource: pipeline/graph_build.py
tags: [datamodel, provenance, belegt_durch, rechtsverbindlichkeit]
timestamp: 2026-06-14
---

# Provenance (`BELEGT_DURCH`)

The system's reason to exist: every extracted entity is provable at the audio second.

- Records carry `quelle_utterances: list[int]` → in `build_graph` become `BELEGT_DURCH →
  Transkriptsegment` edges (see [[transkriptsegment]]).
- An entity without a provenance edge is a **bug** (CLAUDE.md gotcha #3).
- GraphRAG answers surface it as `↳ Audiobeleg [mm:ss]`; the web UI deep-links the audio.
- Pages projection of official sessions is a slim structure projection (no `Transkriptsegment`
  nodes); the full provenance graph lives in Neo4j.

**Source:** `CLAUDE.md` gotcha #3; `README.md:103-106`; `.claude/rules/api-conventions.md §2`;
ADR-0005.
