---
type: datamodel
title: FactCheck & Quelle
description: Verdict scale + the mandatory-source invariant; unbelegt ≠ falsch.
resource: pipeline/factcheck.py
tags: [datamodel, factcheck, invariant]
timestamp: 2026-06-14
---

# FactCheck & Quelle

A `Faktencheck` records a verdict on an `Aussage` with a mandatory source.

- **Verdict scale (fixed, `VERDIKTE`):** `bestätigt · teilweise · irreführend · falsch ·
  unbelegt` (`factcheck.py:25`).
- **Invariant:** every `FactCheck` has a `quelle` — `assert all(fc.quelle for fc in results)`
  (`factcheck.py:238/277/392`). `unbelegt` cites the corpus it was checked against + `stand`,
  never an empty result.
- **`Quelle` shape:** `{titel, stand, url}`.
- **Graph:** `Aussage -[:GEPRUEFT_ALS]-> Faktencheck -[:BELEGT_MIT]-> Quelle`.
- **Real persons:** verdicts carry `_LLM_DISCLAIMER` (`factcheck.py:282`) +
  `metadata.factcheck_disclaimer`; human-in-the-loop before publication.

**Source:** `pipeline/factcheck.py`; `.claude/rules/api-conventions.md §3`; ADR-0006, ADR-0007.
See also [[provenienz-belegt-durch]].
