---
title: All-81 YouTube completeness + aggregate dashboard
status: current
owner: ma3u
updated: 2026-06-14
adr: ["0013"]
knowledge: ["docs/knowledge/apis/youtube-mediathek.md"]
---

# All-81 YouTube completeness + aggregate dashboard

Surveyed and structurally ingested every WP21 session that has @bundestag /videos clips, via the
official YouTube Data API v3 (ADR-0013), and built an aggregate dashboard over all sessions.

**Source:** `docs/challenge-plan.md:43` (row 19); GCP API survey 2026-06-14.

## Completeness — YouTube clips (Data API survey)

- **56 / 81** sessions have clips → **structurally ingested** (377 clips, 1240 nodes). Full
  graphs in `output/yt_21_*_graph_data.json` (gitignored); summary committed to
  `web/data/youtube_completeness.json`.
- **25 / 81** have **no** clips (covered by amtliches XML already in Neo4j):
  3, 4, 5, 6, 9, 11, 12, 13, 16, 17, 19, 20, 23, 25, 26, 29, 30, 33, 36, 39, 44, 45, 46, 52, 55.
- Top coverage: Sitzung 59 (25 clips), 80 (23), 68 (22), 65 (19), 62 (17).

Regenerate: `python3 scripts/youtube_survey.py` · `python3 scripts/ingest_all_youtube_clips.py`.

## Aggregate dashboard — DONE

`web/aggregate.html` (+ `web/data/aggregate_dashboard.json`, built by
`scripts/aggregate_dashboard.py`, dep-free). Sections: Kennzahlen · Themen nach Redevolumen ·
Top-Redner:innen · Faktencheck-Verdikt-Verteilung · **Aussagen je Person (faktenbasiert vs.
fragwürdig — KI-Vorschlag, kein Urteil)** · je Fraktion · Trend je Sitzung · YouTube-Abdeckung ·
Fun Facts. Verdict data from the 13 LLM-checked showcase graphs (70–81 + 20/214); topics/redner
from all 82 dashboards.

Verdikt gesamt (Showcase): bestätigt 115 · teilweise 293 · irreführend 42 · falsch 60 ·
unbelegt 93. The fact-check carries the `_LLM_DISCLAIMER` banner (ADR-0007/-0006).

## Status checklist

- [x] GCP API survey of all 81 (`youtube_api.all_session_clips`, `scripts/youtube_survey.py`).
- [x] Structural ingest of the 56 with clips (`scripts/ingest_all_youtube_clips.py`).
- [x] Aggregate dashboard JSON + accessible HTML (rendered/verified desktop + mobile).
- [ ] Captions (yt-dlp) + LLM fact-check for the 56 → real per-speaker verdicts on the YouTube
      graphs (cost/time) — see [`../future/youtube-clips-bulk-ingest.md`](../future/youtube-clips-bulk-ingest.md).
- [ ] Publish the 56 `yt_` graphs to Pages/Neo4j (`ingest_youtube_clips.py <nr> --load`) — opt-in
      to avoid web/data bloat.
- [ ] Link `aggregate.html` from `web/index.html`.

## Notes / caveats

- YouTube auto-captions have **no speaker labels** → per-speaker fact/lie comes from the
  **amtlich** graphs, not the YouTube clips (ADR-0008). The dashboard reflects this.
- `_TOP` regex still mis-splits comma-listed TOPs ("TOP 8, ZP 2,3: …").
