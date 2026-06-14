---
type: runbook
title: E2E tests
description: The venv pytest suite (~250 cases) against real sessions in local Neo4j.
resource: tests/
tags: [runbook, tests, pytest, e2e]
timestamp: 2026-06-14
---

# Runbook — E2E tests

Two verification layers: the dep-free demos ([[demo-dep-free]], CI baseline) and this venv E2E
suite (not in CI — needs Neo4j + a loaded graph).

```bash
.venv/bin/pip install -r requirements-test.txt
NEO4J_URI=bolt://localhost:7688 .venv/bin/python -m pytest tests/ -q     # → 251 passed
```

~250 cases: positive (data landed/correct, provenance, persons, embeddings — 449 vectors, dim
3072) + negative (`_SAFE`/injection rejection, namespacing, **0** auto-verdicts on real persons,
malformed XML → clean `ParseError`, absent data → empty). Neo4j tests **skip** (not fail) when
Neo4j is unreachable. Don't claim the E2E suite passed without a loaded Neo4j.

**Source:** `.claude/rules/testing.md`; `README.md:342-361`; `tests/`.
