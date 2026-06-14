---
type: service
title: Dashboard & accessible
description: Per-session KPIs and a screen-reader/TTS-friendly linear narrative.
resource: pipeline/dashboard.py
tags: [service, dashboard, accessibility, barrierefreiheit]
timestamp: 2026-06-14
---

# Dashboard & accessible

- **`dashboard.py`** → `web/data/*_dashboard.json` ("📊 Dashboard"): top themes by speech
  volume, speech share per faction, positive/negative feedback per theme & faction (from
  Saalreaktionen), fact-check balance.
- **`accessible.py`** → "♿ Vorlesefassung": linear, screen-reader/TTS-friendly text including
  **verbalized Saalreaktionen** (Beifall = Zustimmung, Widerspruch/Buhrufe = Ablehnung) and
  fact-check with sources. `_VERDIKT_WORT` verbalizes verdicts. a11y-audited (axe-core 0
  violations).
- **`gap_analysis.py`** / `compare_protocol_video.py`: WER, Saalreaktions-Recall, speaker/content
  gaps vs. the amtlicher Goldstandard.

**Source:** `README.md:230-242`; `pipeline/dashboard.py`, `accessible.py`, `gap_analysis.py`.
