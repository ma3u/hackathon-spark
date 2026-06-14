---
title: Extend fact-check retrieval grounding to all 81 sessions
status: future
owner: ma3u
updated: 2026-06-14
adr: ["0006", "0007"]
knowledge: ["docs/knowledge/services/factcheck.md"]
---

# Extend fact-check retrieval grounding to all 81 sessions

Retrieval-grounded fact-checking (Brave + DIP-API + Wikipedia) currently covers the showcase
sessions 70–81. Extend it to all 81 WP21 sessions.

**Status:** future. Source: `docs/challenge-plan.md:91-92` (Schritt 1, optional),
`:73` (risk row).

- **Constraint:** Brave free-plan rate/cost limit on a full run of all 81
  (`challenge-plan.md:73`). Mitigation: throttle `_chat_retry`, cache results, or run in
  batches.
- Keep the invariants: every verdict carries a `Quelle` (ADR-0006); real-person verdicts carry
  the `_LLM_DISCLAIMER` + human-in-the-loop (ADR-0007).
