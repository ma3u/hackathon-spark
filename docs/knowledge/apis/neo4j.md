---
type: api
title: Neo4j
description: The knowledge-graph store and GraphRAG/Text2Cypher backend.
resource: docker-compose.neo4j.yml
tags: [api, neo4j, graph, bolt, cypher]
timestamp: 2026-06-14
---

# Neo4j

Local Neo4j 5 (Community) stores the full graph and backs GraphRAG.

- **Connection (env):** `NEO4J_URI` (`bolt://localhost:7687`, or `7688` for the real-sessions
  stack), `NEO4J_USER` (`neo4j`), `NEO4J_PASSWORD` (`healthdataspace` in the bundled compose).
- **Start:** `docker compose -f docker-compose.neo4j.yml up -d` (ports overridable via
  `NEO4J_HTTP_PORT` / `NEO4J_BOLT_PORT`).
- **Scale (loaded):** all 81 WP21 + WP20/214 → ~136 k Knoten / ~361 k Beziehungen; 449 vectors,
  dim 3072, vector index `ONLINE`.
- Loads are idempotent & parameterized with `_SAFE` gating ([[neo4j-loader-graphrag]], ADR-0009).

**Source:** `CLAUDE.md` Build section; `docker-compose.neo4j.yml`;
`.claude/rules/api-conventions.md §4`; `docs/neo4j-echtsitzungen.md`.
