---
title: Gap-diff overlay (word diff) + Diarisierungs-DER
status: future
owner: ma3u
updated: 2026-06-14
knowledge: ["docs/knowledge/runbooks/e2e-tests.md"]
---

# Gap-diff overlay (word diff) + Diarisierungs-DER

Make the protocol↔spoken-word delta visible per speech, and add a diarization-quality metric.

**Status:** future. Source: `docs/challenge-plan.md:95-96`.

- **Gap-diff view:** overlay a word-level diff (Protokoll ↔ gesprochen) per Rede, building on
  the existing `gap_analysis.py` ASR-gap / correction-gap split.
- **DER (Diarization Error Rate):** add a diarization-quality metric (open) — complements the
  WER benchmark ([`../done/wer-benchmark-10-sessions.md`](../done/wer-benchmark-10-sessions.md)).
- Model speakers' Korrekturrecht as a *diff*, never as "falsch" (`challenge-plan.md:75`).
