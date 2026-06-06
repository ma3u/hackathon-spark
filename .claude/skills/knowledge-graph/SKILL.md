---
name: knowledge-graph
description: >-
  Use when extracting structure from a meeting or building/exporting the protocol knowledge
  graph in graph-protokoll: turning Utterances into a Protocol, building the SPARK-format
  graph, the 5-layer ontology (normativ/zeitlich/prozedural/fallbezug/provenienz), provenance
  edges, and JSON/CSV/Cypher/Neo4j export. Trigger on pipeline/extract.py, graph_build.py,
  export.py, neo4j_loader.py, node/relationship/ontology/Cypher work.
---

# Knowledge graph (Protocol → SPARK graph → Neo4j)

The heart of the project: structured public-administration facts as a verifiable graph.

## Flow

```
Utterances ─→ extract.extract_rule_based ─→ Protocol ─→ graph_build.build_graph ─→ {metadata,nodes,relationships}
   (or bundestag_xml.parse_plenarprotokoll)                 ├─ export.write_json / write_csv / write_cypher
                                                            └─ neo4j_loader.load_graph (idempotent MERGE)
```

- **`Protocol`** (`extract.py`) is the shared model — see `.claude/rules/api-conventions.md §2`
  for its fields. The rule-based extractor uses German-aware regex (`_split_sentences` keeps
  "30. Juni" intact; `_is_checkable` separates facts from promises). The LLM Produktivpfad is
  specified by `EXTRACTION_PROMPT` (raises `NotImplementedError` until wired to a local LLM).
- **`build_graph`** emits the SPARK format and tags every node with a `schicht`
  (ontology layer). Layers: **L1 normativ** (`Norm`, e.g. GemO §37/§18), **L2 zeitlich**
  (`Sitzung`, Fristen), **L3 prozedural** (`Tagesordnungspunkt → Antrag → Abstimmung →
  Beschluss → Aufgabe`), **L4 fallbezug** (`Person`, `Fraktion`, `Redebeitrag`, `Aussage`,
  `Frage`, `AkustischesEreignis`), **provenienz** (`Transkriptsegment`), plus `faktencheck`.

## Rules when editing

- **Don't break the SPARK contract.** Reserved keys (`id,label,type,subtype` /
  `source_id,target_id,relationship_type`), stable slug IDs (`_slug`, `person_…`, `top_…`,
  `segment_<idx>` pinned to the utterance index). Set `schicht` on every node.
- **Provenance is mandatory.** Use the `belegt(entity_id, src_list)` helper so every entity
  with `quelle_utterances` gets a `BELEGT_DURCH → Transkriptsegment` edge. The audio-second
  proof is what makes this a justiziables Protokoll, not a summary.
- **Add a node label or rel type?** Update **three** places to keep them in sync: `build_graph`,
  the Neo4j `NEO4J_SCHEMA` (in `neo4j_graphrag.py`), and the web frontend `LAYER`/legend if a
  new `schicht` appears.
- **Export & Neo4j:** `export.py` writes JSON/CSV/Cypher in the format the React/3d-force-graph
  frontend and Neo4j both read. `neo4j_loader.build_statements` uses **parameterized** Cypher
  + `_SAFE`-gated labels and idempotent `MERGE` — never string-interpolate data.
- Keep `metadata.node_count`/`relationship_count` consistent with the actual lists.

## Verify

`python3 run_demo.py` and `python3 ingest_bundestag.py` (dry-run prints node/rel counts).
For a real load: `docker compose -f docker-compose.neo4j.yml up -d` then
`python3 ingest_bundestag.py --xml <prot>.xml --load`.
