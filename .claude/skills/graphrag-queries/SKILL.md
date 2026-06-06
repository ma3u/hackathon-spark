---
name: graphrag-queries
description: >-
  Use when answering natural-language questions over the protocol graph in graph-protokoll:
  the offline intent-router (pipeline/graphrag.py), the Neo4j Text2Cypher path
  (pipeline/neo4j_graphrag.py), the NEO4J_SCHEMA / few-shot examples, multi-hop traversals, or
  query-with-provenance work. Trigger on GraphRAG/Cypher/Text2Cypher/"ask the graph" tasks.
---

# GraphRAG queries (multi-hop questions with audio provenance)

Protocol questions are **multi-hop and structured** ("which Beschluss from which Abstimmung
under which TOP — and where in the audio?"), which is why this uses a graph, not flat vector
RAG. There are two implementations sharing one mental model.

## Two paths

| File | Path | What |
| ---- | ---- | ---- |
| `pipeline/graphrag.py` | Demopfad | `GraphRAG.ask(frage)` — deterministic **intent router** over the in-memory graph (`GraphIndex`: `out`/`inc`/`by_type`/`provenance`). Each answer ends with `↳ Audiobeleg [mm:ss]`. No LLM, no Neo4j. |
| `pipeline/neo4j_graphrag.py` | Produktivpfad | Official `neo4j-graphrag` **Text2Cypher**: NL question → schema-guided Cypher → Neo4j → LLM answer. LLM via `OpenAILLM` `base_url` → local Ollama/vLLM (on-prem, no cloud). |

```bash
# demo router (stdlib): run_demo.py asks the scenario questions
python3 run_demo.py --scenario gemeinderat
# production (needs Neo4j loaded + a local LLM):
python3 -m pipeline.neo4j_graphrag "Welche Aussagen sind falsch — mit Quelle?"
```

## When editing

- **Keep `NEO4J_SCHEMA` truthful.** It lists the node labels + relationships Text2Cypher is
  allowed to use. Whenever `build_graph` adds/renames a label or edge, update this schema (and
  the demo router's traversals) to match — a drifted schema produces wrong Cypher.
- **Fact-check answers must cite.** The few-shot `EXAMPLES` are written so verdict queries
  always return verdict **and** `q.label`/`q.url`. Preserve that when adding examples; the
  fact-check sourcing invariant extends to query answers.
- **Provenance in answers.** In the demo router, surface `provenance(nid)` (`BELEGT_DURCH →
  Transkriptsegment`, sorted by `start_sec`) via `_cite`. Don't return claims without their beleg.
- The router matches German keywords (`faktencheck`, `beschlussfähig`, `befangen`, `aufgabe`,
  `abstimmung`, …). Extend the keyword map and add a matching `by_type`/traversal method when
  adding a query type; keep the fallback hint listing the supported questions.
- On-prem: never point the LLM at a cloud endpoint by default — `llm_base_url` targets a local
  OpenAI-compatible server.

## Verify

`python3 run_demo.py` (both scenarios print Q&A with belege). For Text2Cypher, a live Neo4j
(`docker compose -f docker-compose.neo4j.yml up -d`, then `--load`) and a local LLM are needed.
