---
type: api
title: YouTube & Bundestag Mediathek
description: Video sources — YouTube full streams (auto-captions) and Mediathek (speaker-accurate).
resource: pipeline/mediathek.py
tags: [api, youtube, mediathek, video, deeplink]
timestamp: 2026-06-14
---

# YouTube & Bundestag Mediathek

Two video sources feeding the `yt_` graph and the official graph's per-speech deep-links.

- **YouTube @bundestag/streams** — Gesamtmitschnitte with auto-captions (VTT) →
  `subtitles.youtube_segments` → `yt_<wp>_<nr>` graph with time deep-links. Only ~recent
  streams available; ASR-gap high (41% / 21% on sessions 79 / 81).
- **Bundestag Mediathek** — corrected, speaker-attributed captions (`pipeline/mediathek.py`);
  per-speech video deep-link merged into the **official** graph (`Redebeitrag.video_url`); 7388
  Reden linked across all 81 (`scripts/mediathek_links.py`).
- **YouTube clips (`/videos`)** — per-TOP clips for stream-less sessions. Discovery is moving
  from yt-dlp scraping (`pipeline/youtube_clips.py`) to the **official YouTube Data API v3**
  (`YOUTUBE_API_KEY`); captions stay on yt-dlp. See ADR-0013 +
  [[../planning/current/youtube-data-api-integration]].

**Source:** `README.md:263,247-277`; `docs/youtube-sitzungen-wp21.md`. ADR-0008.
