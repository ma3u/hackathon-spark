---
title: Fact-check retrieval grounding (Brave + DIP + Wikipedia)
status: done
owner: ma3u
updated: 2026-06-14
adr: ["0006", "0007"]
knowledge: ["docs/knowledge/services/factcheck.md"]
---

# Fact-check retrieval grounding (Brave + DIP + Wikipedia)

Closed the old "corpus too general → everything unbelegt" gap: `factcheck_with_retrieval` uses
Brave web search + DIP-API + Wikipedia as the evidence corpus, and the LLM judges the claim
against the retrieved Belege (throttled `_chat_retry` ≈ 1 call/s + backoff).

**Status:** done for the showcase. Source: `docs/challenge-plan.md:42` (table row 16),
`:62-69` (Fortschritts-Log).

- Sessions 70–81 grounded with varied verdicts + real authoritative sources (destatis.de,
  tagesschau.de, dip.bundestag.de, bundesfinanzministerium.de, bmi.bund.de,
  bundesrechnungshof.de) — `challenge-plan.md:62-69`.
- Example (session 81): 24 teilweise / 9 bestätigt / 5 irreführend / 2 falsch / 12 unbelegt
  (`challenge-plan.md:69`).
- Run: `sync_sessions.py --official --web-graph --retrieval`.

Every verdict keeps its `Quelle` (ADR-0006) and, on real persons, the `_LLM_DISCLAIMER`
(ADR-0007). Extending grounding to all 81 is tracked in
[`../future/grounding-all-81.md`](../future/grounding-all-81.md).
