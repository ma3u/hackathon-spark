---
title: Audio pipeline + SPARK graph + outputs
status: done
owner: ma3u
updated: 2026-06-14
adr: ["0003", "0004", "0005", "0012"]
knowledge: ["docs/knowledge/services/audio-front.md", "docs/knowledge/datamodels/spark-graph-format.md"]
---

# Audio pipeline + SPARK graph + outputs

The base product: audio → sprecher-attribuierte Utterances → `Protocol` → 5-layer SPARK graph,
with the dep-free Demopfad as the always-on smoke test, plus the dashboard, accessible
(Vorlesefassung) and export outputs, and the E2E test suite.

**Status:** done. Source: `docs/challenge-plan.md:24-29` (rows 1, 2, 5), README pipeline section.

- ASR → Diarisierung → Alignment (`pipeline/asr,diarize,align.py`) — `challenge-plan.md:24`.
- Extraktion + 5-Schichten-Graph in SPARK format (`pipeline/extract.py`, `graph_build.py`).
- Neo4j import: idempotent, parametrized, namespaced (`pipeline/neo4j_loader.py`) —
  `challenge-plan.md:28`.
- Dashboard + accessible text (`pipeline/dashboard.py`, `accessible.py`).
- E2E tests against real Neo4j data (`tests/`) — `challenge-plan.md` row 18.

**Verify:** `python3 run_demo.py` (both scenarios, dep-free).
