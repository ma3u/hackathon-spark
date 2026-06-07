# CLAUDE.md — graph-protokoll

SPARK-Hackathon **Challenge 2** prototype. Turns a meeting recording (Gemeinderat,
Ausschuss, **Bundestag**) — or an official Bundestag plenary-protocol XML — into a
**verifiable knowledge graph + fact-check + dashboard**, queryable via Neo4j-GraphRAG.
Every extracted statement is provable down to the audio second (`BELEGT_DURCH`).

Code, docs, and domain identifiers are **German**. Demo data is **entirely fictional**.

## Build & run commands

The demo path needs **only Python 3.11+ (stdlib)** — no GPU, models, network, or pip.

```bash
python3 run_demo.py                       # both scenarios (gemeinderat + bundestag)
python3 run_demo.py --scenario bundestag  # one scenario (+ fact-check)
python3 run_demo.py --no-queries          # only (re)generate web/data/*.json
python3 run_demo.py --audio path/to.mp3   # real audio → needs pip deps (see below)

python3 ingest_bundestag.py --xml prot.xml          # official XML → graph (dry-run Neo4j)
python3 ingest_bundestag.py --xml prot.xml --load   # actually load into Neo4j
python3 ingest_bundestag.py --xml data/real/plenarprotokoll-20-214.xml \
        --name bundestag_real --no-factcheck        # real session, NO verdicts on real people
python3 compare_protocol_video.py                   # gap analysis self-test (WER/recall)

python3 -m http.server -d web 8000        # serve the Pages app at localhost:8000
```

Production path (real audio / live Neo4j / Text2Cypher):

```bash
pip install -r requirements.txt                      # faster-whisper, pyannote, neo4j, …
docker compose -f docker-compose.neo4j.yml up -d     # local Neo4j 5 (neo4j/healthdataspace)
python3 -m pipeline.neo4j_graphrag "Welche Aussagen sind falsch — mit Quelle?"
./scripts/fetch-session.sh 21 81                     # pull official sources (runs on YOUR machine)

# Multiple REAL sessions fully into one local Neo4j (ports overridable if 7474/7687 taken):
NEO4J_HTTP_PORT=7475 NEO4J_BOLT_PORT=7688 docker compose -f docker-compose.neo4j.yml up -d
export NEO4J_URI=bolt://localhost:7688
python3 scripts/load_real_sessions.py                # load data/real/*.xml (namespaced, factcheck off)
python3 scripts/verify_neo4j.py                      # automated checks (3 real-case scenarios)

# GenAI stack (venv; LLM via .env — Azure AI Foundry, OpenAI-compatible. NEVER commit .env):
.venv/bin/pip install -r requirements-genai.txt      # neo4j-graphrag, graphdatascience, haystack
.venv/bin/python scripts/graphrag_compare.py         # Text2Cypher: Mistral-Large-3 vs Kimi-K2.6
.venv/bin/python scripts/gds_analysis.py             # GDS: PageRank / Louvain / Degree
.venv/bin/python scripts/haystack_neo4j.py "Frage"   # Haystack→Neo4j full-text RAG + Azure
.venv/bin/python scripts/vector_search.py "Frage"    # vector/semantic RAG (text-embedding-3-large)
```

There is **no test framework** yet (no pytest/CI tests). Verification = running the
reproducible demos above + the `factcheck.py` invariant `assert`. See `.claude/rules/testing.md`.

## Architecture

A linear **pipeline** with **two input fronts** that converge on one `Protocol` dataclass:

```
Audio  → asr → diarize → align ─┐
                                ├─→ extract → Protocol → graph_build → export → GraphRAG
Official XML → bundestag_xml ───┘            (+ factcheck, sound_events, dashboard, accessible)
```

- **`Protocol`** (`pipeline/extract.py`) is the central data model: `tops, antraege,
  abstimmungen, beschluesse, befangenheiten, aufgaben, redebeitraege, aussagen, fragen,
  kommentare, utterances`. Both input fronts produce it; everything downstream consumes it.
- **`build_graph`** (`pipeline/graph_build.py`) emits the **SPARK graph format**
  `{metadata, nodes, relationships}` — shared with sister prototypes (graph-insurance/
  -investigation/-eAkte), the web frontend, and Neo4j. A 5-layer ontology lives in the
  `schicht` property: `normativ · zeitlich · prozedural · fallbezug · provenienz`.
- **Dual-path modules**: each pipeline module ships a *Produktivpfad* (heavy/real, e.g.
  `transcribe`, `factcheck_with_retrieval`) and a *Demopfad* (stdlib, deterministic, e.g.
  `load_pretranscribed`, `factcheck_rule_based`). The demo path must always run dep-free.
- **GraphRAG** has two implementations: `graphrag.py` (offline intent-router over the
  in-memory graph, demo) and `neo4j_graphrag.py` (official Text2Cypher, production).

## Key directories

| Path | What |
| ---- | ---- |
| `pipeline/` | All processing modules (one concern per file). The whole product lives here. |
| `run_demo.py` / `ingest_bundestag.py` | The two entry points (audio demo · official XML). |
| `data/sample/` | **Fictional** diarized recordings + sample plenary XML. |
| `data/evidence/evidenz.json` | **Fictional** evidence corpus for the fact-checker. |
| `data/real/` | **Real**, gemeinfreie official protocol(s) → `bundestag_real` scenario (fact-check off). |
| `web/` | Static single-file Pages app (`index.html`, `3d-force-graph` via CDN). |
| `web/data/*.json` | Generated graph/dashboard data — **tracked on purpose** (see gotchas). |
| `output/` | Generated JSON/CSV/Cypher artifacts — **gitignored**. |
| `scripts/` | `fetch-session.sh`, `resolve-session.py`, `publish-to-github.sh`. |
| `docs/` | Challenge plan, Bundestag analysis, sources. Read these before changing behavior. |

## Coding conventions

- **German domain vocabulary** in identifiers and strings (Beschluss, Abstimmung,
  Befangenheit, Aufgabe, Redebeitrag, Aussage, Faktencheck, Quelle, Saalreaktion). Keep it.
- Every module starts with `from __future__ import annotations` and a German docstring that
  names its **Produktivpfad** and **Demopfad**.
- Heavy deps (`faster_whisper`, `pyannote`, `torch`, `neo4j`, `neo4j_graphrag`, `librosa`,
  `numpy`, `panns_inference`) are **lazy-imported inside functions** — never at module top.
- Structured data uses `@dataclass` (`Word`, `AsrResult`, `SpeakerTurn`, `Utterance`,
  `Protocol`, `FactCheck`). Pass-through dicts use the JSON keys above verbatim.
- Type hints use 3.10+ syntax (`str | None`, `list[dict]`). 4-space indent, no formatter config.
- Stable, slugified node IDs via `_slug` (`person_…`, `top_…`, `segment_{idx}`). Don't churn IDs.

See `.claude/rules/code-style.md` and `.claude/rules/api-conventions.md` for details.

## Top 5 gotchas (project-specific)

1. **Don't break the stdlib-only demo.** `run_demo.py`, `ingest_bundestag.py`,
   `compare_protocol_video.py` and CI (`.github/workflows/pages.yml`) run with **zero pip
   deps**. Any new heavy import must be lazy (inside the function), behind a Produktivpfad.
2. **Fact-check invariant: every `FactCheck` carries a `Quelle` — always.** Enforced by the
   `assert` in `factcheck.py`. `unbelegt` ≠ `falsch`: an unproven claim still cites the
   *corpus it was checked against* (with `stand`). Never drop the source to mean "no result".
3. **Provenance is mandatory.** Every extracted entity carries `quelle_utterances` (segment
   indices) → `BELEGT_DURCH` → `Transkriptsegment.start_sec`. New entities without a
   provenance edge are a bug — the audio-second proof is the whole point (Rechtsverbindlichkeit).
4. **The SPARK graph format is a contract.** Node keys `{id,label,type,subtype,…}` and
   relationship keys `{source_id,target_id,relationship_type,…}` are read by Neo4j, the web
   frontend, and sister prototypes. Don't rename them. `schicht` drives frontend coloring.
5. **Neo4j safety + data-source discipline.** Labels/rel-types are validated by the `_SAFE`
   regex and data is passed as **parameters** (never string-interpolated) — keep it that way to
   avoid Cypher injection. On data: `data/sample/` + `data/evidence/` are **fictional** (never
   fabricate real-looking people/quotes/numbers there); `data/real/` is **real & gemeinfrei**.
   Hard rule: **never run the fact-checker on real, named people for publication** — real
   sessions are ingested with `--no-factcheck` (no `Faktencheck`/`Quelle`/`GEPRUEFT_ALS` on real
   persons). The fact-check invariant in gotcha #2 still holds for the fictional scenario.
   See `docs/spark-und-echtdaten.md`.
