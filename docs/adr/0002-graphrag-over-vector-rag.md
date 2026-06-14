# 0002. Use a Neo4j knowledge graph + GraphRAG, not vector-RAG alone

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since project start)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `README.md:112-133`; `CLAUDE.md` "Architecture"; `pipeline/neo4j_graphrag.py`;
  `docs/neo4j-echtsitzungen.md`

## Context

Protocol questions are **multi-hop and structured** — "which decisions led to which result?",
"who was conflicted under which norm?", "how was the vote on the Bücherbus?". An embedding index
over text chunks cannot traverse `TOP → Abstimmung → Beschluss` or `Person → BEFANGEN_BEI →
Norm`. The reference SPARK Workflow (BMDS) uses Qdrant / vector-RAG and has *no* graph
(`README.md:297-308`).

## Decision

We will model the protocol as a **Neo4j knowledge graph** and answer questions with **GraphRAG /
Text2Cypher** (`pipeline/neo4j_graphrag.py`, the official `neo4j-graphrag` library). A dep-free
offline intent-router (`pipeline/graphrag.py`) covers the demo. Three complementary retrieval
paths run over the same graph: structured (Text2Cypher), keyword (Haystack full-text), and
semantic (native Neo4j vector index, `scripts/vector_search.py`).

## Consequences

- Multi-hop queries return answers **with audio provenance** (`↳ Audiobeleg`); this is the
  product's differentiator vs. SPARK (`README.md:300-308`).
- Adds a Neo4j operational dependency for the production path (mitigated: demo path is graph-in-
  memory, dep-free).
- A node label / relationship added to `build_graph` must be mirrored in `NEO4J_SCHEMA`
  (Text2Cypher few-shots) — see ADR-0003.

## Alternatives considered

- **Vector-RAG alone (Qdrant, like SPARK)** — rejected: cannot express procedural/normative
  traversal; would lose the legal-verifiability story. Kept as a *complementary* third path, not
  the primary retriever.
