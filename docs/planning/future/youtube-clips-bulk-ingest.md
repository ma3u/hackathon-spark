---
title: Bulk-ingest the 42 YouTube-confirmed stream-less sessions (clips)
status: future
owner: ma3u
updated: 2026-06-14
adr: ["0013", "0008"]
knowledge: ["docs/knowledge/apis/youtube-mediathek.md"]
---

# Bulk-ingest the 42 YouTube-confirmed stream-less sessions (clips)

The Data-API clip-discovery capability exists and is verified
([`../done/youtube-data-api-integration.md`](../done/youtube-data-api-integration.md)). Now use
it to actually ingest the **42 YouTube-confirmed sessions that have no full @bundestag stream**
as a 🎬 source.

**Status:** future. Source: `docs/challenge-plan.md:43` (row 19); ADR-0013.

## Scope

- For each of the 42 sessions: `ingest_youtube_clips(wp=21, nr=…, captions=True, load=True)` →
  `yt_<wp>_<nr>` graph (TOP topics + per-clip video deep-links), persons global (ADR-0008).
- Batch via `scripts/ingest_youtube_clips.py` (loop) or extend `scripts/sync_sessions.py` with a
  `--youtube-clips` action mirroring the existing `--youtube` (streams) path.

## Constraints / risks

- Data API quota ≈ 10k units/day; `playlistItems.list` = 1 unit/page → cheap. Caption fetch is
  yt-dlp per clip (rate-limit + slow) — throttle / run in batches.
- Captions are auto-generated (no speaker labels) → the Mediathek stays the better official
  source where available (ADR-0008); clips fill the gaps.
- web/data growth (committed) — prefer structural projection / dashboards on Pages, full graph in
  Neo4j.
