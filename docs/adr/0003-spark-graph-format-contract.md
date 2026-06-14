# 0003. Treat the SPARK graph format as a cross-project contract

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since project start)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `pipeline/graph_build.py:1-12`; `CLAUDE.md` gotcha #4;
  `.claude/rules/api-conventions.md §1`
- **Diagram:** [`docs/diagrams/graph-ontology-er.mmd`](../diagrams/graph-ontology-er.mmd)

## Context

The built graph `{metadata, nodes, relationships}` is read by **four independent consumers**:
Neo4j (`neo4j_loader.py`), the CSV/Cypher export (`export.py`), the web frontend
(`web/index.html`), and the sister prototypes graph-insurance / -investigation / -eAkte
(`graph_build.py:4`). Renaming a key silently breaks consumers that this repo cannot see.

## Decision

We will treat the node keys `{id, label, type, subtype, schicht}` and relationship keys
`{source_id, target_id, relationship_type}` as a **frozen contract**. `type` becomes the Neo4j
node label; `relationship_type` becomes the rel type. Every node carries a `schicht` (ADR-0011).
IDs are stable slugs (`person_…`, `top_…`, `segment_<idx>`) pinned to the utterance index so
provenance and reactions line up. The `web/data/*.json` outputs are tracked in git on purpose,
so the contract is visible.

## Consequences

- Cross-tool interoperability and a stable frontend; reserved keys never get renamed.
- New per-node/-edge data goes in *free* properties, never by repurposing reserved keys.
- Changing the contract is a breaking change requiring a superseding ADR + coordinated update of
  all consumers (`export._RESERVED`, `neo4j_loader` reserved sets, `web` `LAYER`, `NEO4J_SCHEMA`).

## Alternatives considered

- **Per-consumer bespoke shapes** — rejected: O(n) adapters, drift, lost sister-prototype reuse.
