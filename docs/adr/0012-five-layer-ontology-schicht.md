# 0012. Five-layer ontology carried in a `schicht` property

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since project start)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `pipeline/graph_build.py:6-12`; `README.md:138-147`;
  `.claude/rules/api-conventions.md §1`; `CLAUDE.md` "Architecture"
- **Diagram:** [`docs/diagrams/graph-ontology-er.mmd`](../diagrams/graph-ontology-er.mmd)

## Context

A protocol graph mixes very different concerns — legal norms, time, procedure, people, and
provenance. Without an explicit layering, queries and the frontend cannot distinguish "a norm"
from "a person" from "an audio segment", and the graph stops being self-documenting.

## Decision

Every node carries a `schicht` ∈ {`normativ, zeitlich, prozedural, fallbezug, reaktion,
faktencheck, provenienz`}. Assignment: `Sitzung` → zeitlich; `Person/Fraktion/Redebeitrag/
Aussage` → fallbezug; `Tagesordnungspunkt/Antrag/Abstimmung/Beschluss/Aufgabe` → prozedural;
`Norm` → normativ (kommunal only — no fake GemO in the Bundestag); `AkustischesEreignis`/
Saalreaktion → reaktion; `Faktencheck/Quelle` → faktencheck; `Transkriptsegment` → provenienz.
`schicht` drives frontend coloring (`web/index.html` `LAYER`, dynamic legend showing only
present layers).

## Consequences

- Self-documenting graph; consistent coloring; layer violations are caught in schema review.
- Setting `schicht` on **every** node is mandatory (part of the SPARK contract, ADR-0003).
- The ontology was corrected once (Sitzung=zeitlich, Person=fallbezug, Norm kommunal-only,
  reaction layer added) — captured here as the current state (`docs/challenge-plan.md §3`).

## Alternatives considered

- **Node label alone, no layer** — rejected: label is the type, not the concern; coloring and
  cross-type grouping would need hardcoded maps in every consumer.
