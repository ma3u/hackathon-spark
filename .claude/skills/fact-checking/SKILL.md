---
name: fact-checking
description: >-
  Use when working on claim verification in graph-protokoll: detecting checkable statements,
  assigning verdicts (bestätigt/teilweise/irreführend/falsch/unbelegt), attaching sources, the
  evidence corpus, or the "every fact-check has a source" invariant. Trigger on
  pipeline/factcheck.py, data/evidence/evidenz.json, Aussage/Verdikt/Quelle/Evidenz tasks.
---

# Fact-checking (Aussage → Verdikt + Quelle + Audio-Beleg)

The project's distinctive feature: quantitative claims in speeches are checked against an
official evidence corpus, and **each verdict always carries a source** plus the audio
timestamp of the original statement.

## How it works

```
extract (Aussage) → factcheck → Faktencheck{verdikt, begründung, quelle} → graph: GEPRUEFT_ALS → BELEGT_MIT
```

- **Demopfad** `factcheck_rule_based(aussagen, evidenz_path)`: deterministic keyword-overlap
  match against `data/evidence/evidenz.json` (≥0.6 → that verdict; else `unbelegt`).
- **Produktivpfad** `factcheck_with_retrieval` (contract only, raises `NotImplementedError`):
  dense retrieval over an official corpus (Destatis, Bundesregierung answers, Drucksachen via
  DIP-API) + an NLI-style LLM verifier (entailment/contradiction) **with citation duty**.
- Claims come from `extract._is_checkable` (a quantifiable figure present, and **not** a
  promise like "wird … vorlegen" — those become `Aufgabe`s, not facts).

## The invariant — do not break it

```python
assert all(fc.quelle for fc in results), "Faktencheck ohne Quelle — verletzt Grundsatz."
```

- **Every `FactCheck` has a `quelle`.** Even `unbelegt` references the *corpus it was checked
  against*, with `stand`: "not provable against source X up to date Y" — **not** "not checked".
  Never produce a verdict without a source; never let the `assert` weaken.
- `unbelegt` ≠ `falsch`. Missing evidence is reported as missing, never as refutation.
- Verdict scale is fixed (`VERDIKTE`): `bestätigt · teilweise · irreführend · falsch ·
  unbelegt`. Don't add verdicts without updating `VERDIKTE`, the `accessible._VERDIKT_WORT`
  verbalization, the web frontend `.fc` styles, and the Neo4j few-shot examples.

## Boundaries (keep these honest)

Opinions are not checked (only quantifiable factual claims); a verdict is a **sourced
suggestion**, not a ruling — always Mensch-im-Loop with a Widerspruchspfad; evidence carries a
`stand` so stale belege are flagged. The demo evidence (`data/evidence/evidenz.json`) is
**fictional** — never add real statistics or real sources to it.

**Hard policy — no verdicts on real people.** The rule-based checker against the fictional
corpus is *not* a reliable fact-checker (it produced a spurious `falsch` on a real MdB when run
on a real protocol). Real sessions are ingested with `--no-factcheck` — **never auto-publish
`Faktencheck`/`Quelle`/`GEPRUEFT_ALS` verdicts on real, named persons** (Persönlichkeitsrecht).
Real fact-checking needs a real evidence corpus + LLM-NLI verifier + human review. The
fact-check *mechanism* is demonstrated only on the fictional `bundestag` scenario. See
`[[bundestag-ingestion]]` and `docs/spark-und-echtdaten.md` Teil D.

## Verify

`python3 run_demo.py --scenario bundestag` (prints the fact-check block); the `assert` runs on
every build. Background: `docs/bundestag-protokollierung-analyse.md §4`.
