---
type: datamodel
title: SPARK graph format
description: The cross-project output contract {metadata, nodes, relationships} read by Neo4j, the web app, and sister prototypes.
resource: pipeline/graph_build.py
tags: [datamodel, contract, spark, graph]
timestamp: 2026-06-14
---

# SPARK graph format

`build_graph` emits, and `export` / `neo4j_loader` / `web/index.html` read:

```json
{ "metadata": { "title": "...", "node_count": 0, "relationship_count": 0,
                "ontology_layers": ["normativ","zeitlich","prozedural","fallbezug","provenienz"] },
  "nodes": [ { "id": "top_7", "label": "...", "type": "Tagesordnungspunkt",
               "subtype": "", "schicht": "prozedural" } ],
  "relationships": [ { "source_id": "...", "target_id": "...", "relationship_type": "HAT_TOP" } ] }
```

## Contract (do not break)

- Reserved node keys `{id, label, type, subtype, schicht}`; relationship keys `{source_id,
  target_id, relationship_type}` — never renamed. `type` → Neo4j label; `relationship_type` →
  rel type.
- Every node has a `schicht` (see [[ontologie-5-schichten]]). IDs are stable slugs.
- Shared with sister prototypes graph-insurance / -investigation / -eAkte.

**Source:** `pipeline/graph_build.py:1-12`; `.claude/rules/api-conventions.md §1`; ADR-0003.
Relationship vocabulary: `.claude/rules/api-conventions.md §5`.
