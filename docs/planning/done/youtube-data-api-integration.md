---
title: YouTube Data API v3 integration (official clip discovery)
status: done
owner: ma3u
updated: 2026-06-14
adr: ["0013", "0008", "0010"]
knowledge: ["docs/knowledge/apis/youtube-mediathek.md"]
---

# YouTube Data API v3 integration (official clip discovery)

Replaced the fragile yt-dlp title-scraping with the **official YouTube Data API v3** for
discovering @bundestag per-TOP clips, and wired it into a clip→graph ingestion path so sessions
without a full stream get a `yt_` graph. Captions stay on yt-dlp (ADR-0013).

**Status:** done (built + verified 2026-06-14). Source: `docs/challenge-plan.md:43` (row 19);
ADR-0013.

## Delivered

- [x] `gcloud` login `mabu.mate@gmail.com` (token valid).
- [x] GCP project `gen-lang-client-0062506054`; **`youtube.googleapis.com` enabled**.
- [x] API key created (restricted to YouTube Data API), stored `YOUTUBE_API_KEY` in `.env`
      (gitignored); placeholder in `.env.example`.
- [x] `pipeline/youtube_api.py` — Data-API discovery client (stdlib `urllib`, reuses
      `youtube_clips` title regexes, `collect_session`-shaped output). Live: 34 clips for #83.
- [x] Wired into `pipeline/session_ingest.py`: `clips_protocol` + `ingest_youtube_clips`
      (discovery via Data API w/ yt-dlp fallback; captions via yt-dlp; `yt_` namespace,
      per-clip video deep-links, persons global — ADR-0008). CLI `scripts/ingest_youtube_clips.py`.
- [x] Verified (#83, `--no-captions --no-web`): 34 clips → 31 TOPs, **101 nodes / 167 rels**,
      SPARK keys + `schicht` intact, counts match, `BELEGT_DURCH=68`, import-clean.

## Remaining (optional, follow-ups)

- Full captions + Pages/Neo4j run for a chosen stream-less session
  (`scripts/ingest_youtube_clips.py <nr> --load`).
- **Bulk-ingest the 42 YouTube-confirmed stream-less sessions** →
  [`../future/youtube-clips-bulk-ingest.md`](../future/youtube-clips-bulk-ingest.md).
- Tighten the shared `_TOP` regex for comma-listed TOPs ("TOP 8, ZP 2,3: …" currently parses
  the whole remainder as the topic) — `pipeline/youtube_clips.py` `_TOP`.
