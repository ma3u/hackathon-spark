---
description: Data-model, graph-format, schema & protocol conventions for graph-protokoll
globs:
  - "pipeline/graph_build.py"
  - "pipeline/export.py"
  - "pipeline/neo4j_loader.py"
  - "pipeline/neo4j_graphrag.py"
  - "pipeline/bundestag_xml.py"
  - "pipeline/extract.py"
  - "pipeline/factcheck.py"
  - "data/**/*.json"
  - "data/**/*.xml"
  - "web/index.html"
---

# API & data-model conventions — graph-protokoll

This project has no HTTP API. Its "interfaces" are **data contracts**: the SPARK graph
format, the central `Protocol` model, the Neo4j schema, and the on-disk JSON/XML formats.
These are consumed by Neo4j, the web frontend, and the sister prototypes — change them only
deliberately.

## 1. SPARK graph format (the output contract)

`build_graph` (and the demos) emit, and `export`/`neo4j_loader`/`web/index.html` read:

```json
{
  "metadata": { "title": "...", "node_count": 0, "relationship_count": 0,
                "ontology_layers": ["normativ","zeitlich","prozedural","fallbezug","provenienz"] },
  "nodes": [ { "id": "top_7", "label": "...", "type": "Tagesordnungspunkt",
               "subtype": "", "schicht": "prozedural" /* + free props */ } ],
  "relationships": [ { "source_id": "...", "target_id": "...",
                       "relationship_type": "HAT_TOP" /* + free props */ } ]
}
```

- **Reserved keys never get renamed:** nodes use `id, label, type, subtype`; relationships use
  `source_id, target_id, relationship_type`. CSV/Cypher export and Neo4j depend on them
  (`export._RESERVED`, `neo4j_loader` reserved sets).
- `type` becomes the **Neo4j node label**; `relationship_type` becomes the **rel type**.
- `schicht` ∈ {`normativ, zeitlich, prozedural, fallbezug, reaktion, faktencheck, provenienz`}
  drives frontend coloring (`web/index.html` `LAYER`, **dynamische Legende** — zeigt nur
  vorhandene Schichten). Set it on EVERY node (`Sitzung`→zeitlich, `Person/Fraktion/Redebeitrag/
  Aussage`→fallbezug, `AkustischesEreignis`/Saalreaktion→reaktion, `Norm`→normativ nur kommunal).
- **Pages-Projektion vs. Neo4j:** der committete Web-Graph der amtlichen Sitzungen ist eine
  schlanke STRUKTUR-Projektion (ohne `Transkriptsegment`-Knoten); der Vollgraph mit Provenienz
  liegt in Neo4j. Der **offizielle** Graph = amtliches XML + Mediathek-Video-Deeplink je Rede
  (`Redebeitrag.video_url`); YouTube ist ein separater Graph.
- **IDs are stable slugs** via `_slug`: `person_<slug>`, `top_<nummer>`, `beschluss_<nr>`,
  `aussage_<i>`, `faktencheck_<i>`, `quelle_<slug>`, `segment_<idx>`. Segment/redebeitrag IDs
  are pinned to the utterance index so reactions/provenance line up — don't renumber them.

## 2. `Protocol` — the central data model (`pipeline/extract.py`)

Both input fronts (audio `align` and `bundestag_xml`) produce a `Protocol` with these lists;
every downstream module consumes it:

`meeting{}`, `tops[]`, `antraege[]`, `abstimmungen[]`, `beschluesse[]`, `befangenheiten[]`,
`aufgaben[]`, `redebeitraege[]`, `aussagen[]`, `fragen[]`, `kommentare[]`, `utterances[]`.

- Every extractable record carries `quelle_utterances: list[int]` (source segment indices).
  These become `BELEGT_DURCH → Transkriptsegment` provenance edges — **never omit them**.
- `top_nummer:int` links records to their TOP. `Utterance` carries `herkunft` =
  `"audio"` | `"protokoll"` | `"audio-SED"`; `timecode` is `mm:ss` for audio, `"Prot."` for XML.
- The LLM extraction contract is the JSON schema in `extract.EXTRACTION_PROMPT` — keep that
  schema and the dataclass fields in sync.

## 3. Fact-check contract (`pipeline/factcheck.py`)

- Verdict scale is fixed: `bestätigt · teilweise · irreführend · falsch · unbelegt`
  (`VERDIKTE`). Don't invent new verdicts.
- **Invariant: every `FactCheck` has a `quelle`** (asserted at the end of
  `factcheck_rule_based`). `unbelegt` still references the searched corpus + `stand`
  ("checked against X up to date Y", not "no check"). In the graph this is always
  `Faktencheck -[:BELEGT_MIT]-> Quelle`.
- `Quelle` shape: `{ "titel", "stand", "url" }`.

## 4. Neo4j conventions (`neo4j_loader.py`, `neo4j_graphrag.py`)

- **Parameterized Cypher only.** Use `MERGE (n:`Label` {id: $id}) SET n += $props` with data
  passed as params — never string-interpolate values. Labels/rel-types are gated by the
  `_SAFE` regex (`^[A-Za-z_][A-Za-z0-9_]*$`) before being embedded.
- Loads are **idempotent**: `CREATE CONSTRAINT IF NOT EXISTS … REQUIRE n.id IS UNIQUE`, then
  `MERGE` nodes, then `MERGE` rels. Dry-run is the default; real loads need `--load`.
- Connection defaults come from env: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
  (`bolt://localhost:7687`, `neo4j` / `healthdataspace` for the bundled docker-compose).
- `NEO4J_SCHEMA` + few-shot `EXAMPLES` in `neo4j_graphrag.py` steer Text2Cypher. When you add
  a node label or relationship to `build_graph`, **update `NEO4J_SCHEMA` to match**, and keep
  fact-check examples returning verdict **and** source.

## 5. Relationship vocabulary

Edges currently emitted (keep names/direction consistent): `HAT_TOP`, `MITGLIED_VON`,
`GELEITET_VON`, `PROTOKOLLIERT_VON`, `BESCHLUSSFAEHIG_NACH`, `BEHANDELT_ANTRAG`,
`ENTSCHIEDEN_DURCH`, `FUEHRT_ZU`, `ERGEBNIS_BESCHLUSS`, `ERZEUGT_AUFGABE`, `BEFANGEN_BEI`,
`BEFANGENHEIT_NACH`, `HAT_REDEBEITRAG`, `ZU_TOP`, `STELLT_FRAGE`, `TAETIGT_AUSSAGE`,
`GEPRUEFT_ALS`, `BELEGT_MIT`, `HAT_REAKTION`, `REAKTION_AUF`, `BELEGT_DURCH` (provenance).

## 6. On-disk input formats

- **Diarized sample JSON** (`data/sample/*.diarized.json`): `{ audio_file, language,
  duration_sec, speaker_map{ LABEL: {name, rolle, fraktion} }, segments[{start,end,speaker,text}] }`.
- **Evidence corpus** (`data/evidence/evidenz.json`): `{ stand, korpus_url, evidenz:[{ id,
  schluesselbegriffe[], verdikt, begruendung, quelle{titel,stand,url} }] }`.
- **Sound events** (`data/sample/*_sound_events.json`): `{ audio_file, events:[{label,
  start_sec, end_sec, score, db}] }`; `label` maps via `sound_events.AUDIOSET_MAP`.
- **Official protocol XML**: DTD `dbtplenarprotokoll` (WP19+), parsed by `bundestag_xml.py`.
  Content lives in `<sitzungsverlauf>` → `sitzungsbeginn`/`tagesordnungspunkt`/`zusatzpunkt`/
  `sitzungsende`; `<kommentar>` carries the official Saalreaktionen (Beifall/Zuruf/Lachen/
  Widerspruch). `data/sample/*.xml` is fictional; `data/real/*.xml` is real & gemeinfrei
  (§5 UrhG). Real sessions are ingested with `--no-factcheck` (no verdicts on real persons).
- External services (production/scripts): Bundestag **Open Data** (XML), **DIP-API**
  (`DIP_API_KEY`, parliamentary materials), YouTube/Mediathek via `yt-dlp`.
