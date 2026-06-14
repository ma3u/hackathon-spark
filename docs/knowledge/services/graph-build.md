---
type: service
title: Graph build
description: Protocol → SPARK-format knowledge graph with the 5 layers + provenance edges.
resource: pipeline/graph_build.py
tags: [service, graph, spark, ontology, export]
timestamp: 2026-06-14
---

# Graph build

`build_graph(p, *, audio_file, sitzung_id, factchecks=None)` turns a [[protocol]] into the
[[spark-graph-format]].

- Assigns `schicht` per node ([[ontologie-5-schichten]]) and emits `BELEGT_DURCH` provenance
  edges ([[provenienz-belegt-durch]]).
- Stable slug IDs via `_slug`; relationship vocabulary in `.claude/rules/api-conventions.md §5`.
- Exporters: `export.py` (JSON / CSV / Cypher). A new label/relationship must be mirrored in
  `NEO4J_SCHEMA` (see [[neo4j-loader-graphrag]]) and the web `LAYER`.

**Source:** `pipeline/graph_build.py`; ADR-0003, ADR-0005, ADR-0012. Skill: `knowledge-graph`.
