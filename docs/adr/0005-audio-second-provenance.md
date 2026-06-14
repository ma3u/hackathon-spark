# 0005. Mandatory audio-second provenance (BELEGT_DURCH)

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since project start)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `CLAUDE.md` gotcha #3; `README.md:103-106`;
  `.claude/rules/api-conventions.md §2`; `docs/bundestag-protokollierung-analyse.md`

## Context

An AI summary of a meeting has no legal standing. To make the output a **justiziables
Protokoll** (Rechtsverbindlichkeit), every extracted claim must be checkable at the exact second
it was spoken — "im Streitfall per Klick im Audio nachhörbar" (`README.md:104-106`).

## Decision

Every extractable record carries `quelle_utterances: list[int]` (source segment indices). In
`build_graph` these become `BELEGT_DURCH → Transkriptsegment` edges, and each
`Transkriptsegment` carries `start_sec`/`end_sec`/`audio_file`. **An entity without a provenance
edge is a bug.** GraphRAG answers surface the proof as `↳ Audiobeleg [mm:ss]`; the web UI deep-
links the audio.

## Consequences

- Legal defensibility and audio deep-links across the UI, dashboard, and accessible text.
- Extraction must always thread `quelle_utterances` through to `graph_build`; tests assert the
  `BELEGT_DURCH` edges exist (`.claude/rules/testing.md`).
- The Pages projection of official sessions is a slim *structure* projection without
  `Transkriptsegment` nodes; the full provenance graph lives in Neo4j
  (`.claude/rules/api-conventions.md §1`).

## Alternatives considered

- **Document-level / TOP-level citation only** — rejected: too coarse to defend a disputed
  single statement.
