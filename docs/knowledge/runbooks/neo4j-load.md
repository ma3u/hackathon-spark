---
type: runbook
title: Neo4j load & verify
description: Start Neo4j, load the graph, run automated checks.
resource: scripts/verify_neo4j.py
tags: [runbook, neo4j, load, verify]
timestamp: 2026-06-14
---

# Runbook — Neo4j load & verify

```bash
# Start local Neo4j 5 (ports overridable if 7474/7687 are taken):
NEO4J_HTTP_PORT=7475 NEO4J_BOLT_PORT=7688 \
  docker compose -f docker-compose.neo4j.yml up -d
export NEO4J_URI=bolt://localhost:7688

python scripts/load_real_sessions.py        # load data/real/*.xml (namespaced, factcheck off)
python scripts/verify_neo4j.py              # automated checks (3 real-case scenarios)

# Query the graph in German (Text2Cypher, production path):
python -m pipeline.neo4j_graphrag "Welche Aussagen sind falsch — mit Quelle?"
```

Loads are idempotent + parameterized with `_SAFE` gating ([[neo4j-loader-graphrag]], ADR-0009).
Credentials default to `neo4j` / `healthdataspace`. Bringing the stack **down** removes volumes —
guarded by the PreToolUse hook + `settings.json` ask.

**Source:** `CLAUDE.md` Build section; [[neo4j]]; `docs/neo4j-echtsitzungen.md`.
