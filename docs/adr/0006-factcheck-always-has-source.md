# 0006. Every FactCheck carries a Quelle; "unbelegt" ≠ "falsch"

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since project start)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `pipeline/factcheck.py:25` (`VERDIKTE`), `:238/:277/:392` (`assert`);
  `.claude/rules/api-conventions.md §3`; `docs/bundestag-protokollierung-analyse.md §4`

## Context

An automated fact-checker that returns "false" without a citation is both untrustworthy and
legally dangerous. Equally, conflating "we found no evidence" with "this is false" is a
fallacy that defames the speaker.

## Decision

The verdict scale is **fixed**: `bestätigt · teilweise · irreführend · falsch · unbelegt`
(`VERDIKTE`). **Every `FactCheck` must carry a `quelle`** — enforced at runtime by
`assert all(fc.quelle for fc in results)` in `factcheck.py`. `unbelegt` still references the
*corpus it was checked against* plus a `stand` date ("not provable against source X up to date
Y"), never an empty result. In the graph this is always `Faktencheck -[:BELEGT_MIT]-> Quelle`.
`Quelle` shape: `{titel, stand, url}`.

## Consequences

- The `assert` is a live guard: its failure is a hard bug, not a warning.
- Adding a verdict means updating `VERDIKTE`, `accessible._VERDIKT_WORT`, the web `.fc` styles,
  and the Neo4j few-shot examples in lockstep.
- Separates evidence-absence from refutation, protecting Persönlichkeitsrecht (→ ADR-0007).

## Alternatives considered

- **Boolean true/false** — rejected: cannot express "irreführend"/"teilweise"/"unbelegt".
- **Allow sourceless "no result"** — rejected: indistinguishable from "false"; breaks trust.
