---
title: WER benchmark over 10 sessions
status: done
owner: ma3u
updated: 2026-06-14
knowledge: ["docs/knowledge/runbooks/e2e-tests.md"]
---

# WER benchmark over 10 sessions

Quantified the protocol↔spoken-word gap at scale: a WER benchmark of the Mediathek (corrected)
captions against the amtliches XML over 10 sessions, distinguishing ASR-gap from correction-gap.

**Status:** done. Source: `docs/challenge-plan.md:32,93-96`; `README.md:94`; memory
`[[bundestag-real-data]]`.

- `scripts/wer_benchmark.py`: Mediathek ↔ amtlich correction-gap **Ø ≈ 1.8 %** over 10
  sessions (≈ 520 k words).
- YouTube auto-caption ASR-gap is far higher (41 % / 21 % on sessions 79 / 81) — the gap
  analysis `--gap` distinguishes the two (`gap_analysis.py`).

Follow-up (gap-diff overlay + DER) tracked in
[`../future/gap-diff-der.md`](../future/gap-diff-der.md).
