---
type: service
title: Neo4j loader & GraphRAG
description: Idempotent parameterized load + Text2Cypher / offline intent-router querying.
resource: pipeline/neo4j_loader.py
tags: [service, neo4j, graphrag, text2cypher, security]
timestamp: 2026-06-14
---

# Neo4j loader & GraphRAG

- **`neo4j_loader.py`** — idempotent, **parameterized** `MERGE` over the official driver;
  labels/rel-types gated by `_SAFE = ^[A-Za-z_][A-Za-z0-9_]*$` (`:18`); `CREATE CONSTRAINT IF
  NOT EXISTS … REQUIRE n.id IS UNIQUE`; dry-run default, `--load` to write. Namespaced IDs
  (`amt_` / `yt_`), global persons (see [[bundestag-opendata-xml]], ADR-0008).
- **`neo4j_graphrag.py`** (Produktiv) — official `neo4j-graphrag` Text2Cypher; `NEO4J_SCHEMA` +
  few-shot `EXAMPLES` steer the LLM; fact-check questions always return verdict **and** source.
- **`graphrag.py`** (Demo) — offline intent-router over the in-memory graph; no Neo4j/LLM.

**Source:** `pipeline/neo4j_loader.py`, `neo4j_graphrag.py`, `graphrag.py`;
`.claude/rules/api-conventions.md §4`; ADR-0002, ADR-0009. Skill: `graphrag-queries`.
