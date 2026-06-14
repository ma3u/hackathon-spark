# 0007. Fact-checking real persons: LLM verdict as a captioned AI suggestion (human-in-the-loop)

- **Status:** Accepted (supersedes the earlier `--no-factcheck` stance for real sessions)
- **Date:** 2026-06-14 (policy change recorded in the repo as 2026-06)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `CLAUDE.md` gotcha #5; `pipeline/factcheck.py:282` (`_LLM_DISCLAIMER`),
  `factcheck_with_llm` / `factcheck_with_retrieval`; `docs/spark-und-echtdaten.md`;
  `docs/challenge-plan.md §3-4`

## Context

The deterministic rule-based checker against the *fictional* `evidenz.json` once produced a
spurious `falsch` on a real MdB when run on a real protocol — a defamation risk
(Persönlichkeitsrecht). The original mitigation was to ingest real sessions with
`--no-factcheck`. But suppressing all checking on real content also removes the product's value
on the data that matters.

## Decision

For **real** sessions (YouTube + amtliches XML) we will run the **LLM verifier**
(`factcheck_with_llm`, Azure Mistral-Large-3), optionally grounded by retrieval (Brave web
search + DIP-API + Wikipedia → `factcheck_with_retrieval`). Every verdict on a real, named
person is explicitly a **KI-Vorschlag (ungeprüft)**: it carries the `_LLM_DISCLAIMER`
("Automatische KI-Einschätzung (ungeprüft) — Vorschlag, kein Urteil; vor Veröffentlichung von
Menschen prüfen.") and the graph sets `metadata.factcheck_disclaimer`, shown as a banner in the
UI and HTML protocol. The `Quelle` invariant (ADR-0006) still holds. The deterministic
`factcheck_rule_based` against fictional `evidenz.json` is for the **fictional demo scenarios
only** — never for real people.

## Consequences

- Real fact-checking becomes possible while keeping a **Mensch-im-Loop** as default: the
  correction/release workflow (M4, `scripts/apply_corrections.py`) lets humans approve, reject,
  or correct each verdict before publication.
- The disclaimer banner must render wherever verdicts on real persons appear.
- Speakers' Korrekturrecht is modelled as a *diff* (gap analysis), never as "falsch"
  (`challenge-plan.md §4`).

## Alternatives considered

- **`--no-factcheck` on all real sessions (previous policy)** — superseded: removes value on
  real data.
- **Rule-based checker on real content** — rejected: not a reliable checker; produced false
  verdicts on real persons.
- **Auto-publish LLM verdicts without disclaimer/review** — rejected: defamation + neutrality
  risk.
