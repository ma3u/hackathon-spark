---
description: Review the current uncommitted changes against graph-protokoll's conventions
allowed-tools: Bash(git diff:*), Bash(git status:*), Read, Grep, Glob
---

You are reviewing the working-tree changes for **graph-protokoll** (SPARK Challenge 2).

## Changes under review

Status:
!`git status --short`

Diff (staged + unstaged):
!`git diff HEAD`

## How to review

Review only the diff above. Give concrete, file:line-anchored feedback grouped by severity
(🚨 blocker · ⚠️ should-fix · 💡 nit). Check, in priority order, the project's load-bearing
invariants — these are the things most likely to be broken:

1. **Stdlib-only demo intact?** No new top-level imports of heavy deps (`faster_whisper`,
   `pyannote`, `torch`, `whisperx`, `neo4j`, `neo4j_graphrag`, `librosa`, `numpy`,
   `panns_inference`, `openai`). They must stay lazy-imported inside functions. `run_demo.py`,
   `ingest_bundestag.py`, `compare_protocol_video.py` must still run on Python 3.11 stdlib.
2. **Fact-check invariant.** Any `FactCheck` produced still carries a `quelle`; `unbelegt`
   still references the corpus + `stand`. The `assert` in `factcheck.py` is not weakened.
3. **Provenance.** New extracted entities carry `quelle_utterances` and get a `BELEGT_DURCH →
   Transkriptsegment` edge in `build_graph`. No silent loss of the audio-second proof.
4. **SPARK format contract.** Reserved keys unchanged (`id,label,type,subtype` /
   `source_id,target_id,relationship_type`); every node has a `schicht`; IDs stay stable
   slugs. If a node label / relationship was added, `NEO4J_SCHEMA` in `neo4j_graphrag.py` was
   updated to match.
5. **Neo4j safety.** Cypher stays parameterized; labels/rel-types pass through `_SAFE`. No
   string-interpolated data.
6. **Style & language.** `from __future__ import annotations` present; German domain
   vocabulary and docstrings (Produktivpfad/Demopfad) preserved; dual-path naming respected.
7. **Fictional data only.** No real persons, real quotes, or real statistics introduced.

Then a short correctness pass (logic bugs, edge cases, regex on German text). Reference
`.claude/rules/*.md` and `CLAUDE.md` for the full conventions. End with a one-line verdict:
ready to commit, or the blockers to resolve first.
