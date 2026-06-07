---
description: Testing & verification standards for graph-protokoll
globs:
  - "tests/**"
  - "test_*.py"
  - "*_test.py"
  - "conftest.py"
  - "compare_protocol_video.py"
  - "pipeline/gap_analysis.py"
alwaysApply: false
---

# Testing & verification — graph-protokoll

**State of the repo:** two layers of verification.
- **Dep-free demos (stdlib)** — the always-on smoke test; no pip/GPU/network. CI runs these.
- **`tests/` E2E suite (pytest, ~250 cases)** — runs in the **venv** against the **real**
  sessions loaded in local Neo4j (`requirements-genai.txt` + `requirements-test.txt`). Positive
  (data landed/correct, provenance, embeddings) + negative (`_SAFE`/injection, namespacing, no
  verdicts on real persons, malformed XML → clean `ParseError`, absent data → empty). Neo4j
  tests **skip** (not fail) when Neo4j is unreachable. Not in CI (needs Neo4j + a loaded graph).
  ```bash
  NEO4J_URI=bolt://localhost:7688 .venv/bin/python -m pytest tests/ -q
  ```
Don't claim the E2E suite passed without a loaded Neo4j; the dep-free demos below are the
baseline anyone can run.

## How the project is verified today

1. **Reproducible demo runs** (the primary smoke test — must succeed dep-free):
   ```bash
   python3 run_demo.py                 # both scenarios end-to-end
   python3 ingest_bundestag.py         # official-XML path → graph (dry-run Neo4j)
   ```
   Both must run on **Python 3.11+ stdlib only** (no pip, GPU, or network). CI runs
   `python3 run_demo.py --no-queries` on every push to `main`.

2. **Built-in self-test** — gap analysis with a synthetic ASR derived from the gold XML:
   ```bash
   python3 compare_protocol_video.py   # prints WER, Saalreaktions-Recall, speaker/content gaps
   ```
   `pipeline/gap_analysis.simulate_asr` injects a known number-swap (`150.000→130.000`), a
   dropped sentence, and a missing speaker, so the metrics are deterministic and checkable.

3. **Runtime invariant** — `pipeline/factcheck.py` ends with
   `assert all(fc.quelle for fc in results)`. Every fact-check must carry a source; this
   `assert` is a live guard, treat its failure as a hard bug.

4. **GraphRAG sanity** — the offline router in `pipeline/graphrag.py` answers the demo
   questions in `run_demo.demo_queries`; eyeball that each answer ends with an `↳ Audiobeleg`.

## Standards to follow IF you add tests

- Prefer the **stdlib `unittest`** (or `pytest` if you add it to a dev-only extra) so the
  default install stays dependency-free. Never make the demo path depend on a test lib.
- Put tests under `tests/` as `test_*.py`. Keep them **offline and deterministic** — use the
  fixtures already in `data/sample/` and `data/evidence/evidenz.json`; do not hit the network,
  Neo4j, or any model. Exercise the **Demopfad** functions, not the heavy `*_with_*` ones.
- Cover the load-bearing invariants and contracts:
  - every `FactCheck` has a non-empty `quelle` (incl. the `unbelegt` corpus reference);
  - every extracted entity that should be provable has `quelle_utterances` → a
    `Transkriptsegment` `BELEGT_DURCH` edge in the built graph;
  - the SPARK graph keys are intact (`id,label,type,subtype` / `source_id,target_id,
    relationship_type`) and `metadata.node_count` / `relationship_count` match the lists;
  - `bundestag_xml.parse_plenarprotokoll` and `align.from_pretranscribed` both yield a
    `Protocol` the same `build_graph` accepts (the two fronts stay interchangeable);
  - `neo4j_loader.build_statements` emits only parameterized Cypher and rejects unsafe
    labels/types (`_SAFE`).
- WER/recall regression: `gap_analysis.wer` and `analyze_gaps` have known outputs on the
  sample — assert against fixed numbers, not ranges, since inputs are fixed.
- Use realistic **fictional** data only — never add real persons, quotes, or statistics to
  fixtures.
