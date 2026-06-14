# 0013. Discover YouTube clips via the official YouTube Data API v3 (yt-dlp stays for captions)

- **Status:** Accepted (implemented 2026-06-14 — `pipeline/youtube_api.py`,
  `session_ingest.ingest_youtube_clips`, `scripts/ingest_youtube_clips.py`)
- **Date:** 2026-06-14
- **Deciders:** maintainer (ma3u)
- **Source(s):** `pipeline/youtube_clips.py:1-55` (current yt-dlp scraping);
  `docs/challenge-plan.md:43` (row 19 — "braucht YouTube Data API Key");
  `docs/planning/current/youtube-data-api-integration.md`; ADR-0008, ADR-0010

## Context

Many WP21 sessions have **no @bundestag full Gesamtmitschnitt** (only the ~5 most recent
streams persist), but the `/videos` tab carries per-TOP clips with the real topic in the title.
Today `pipeline/youtube_clips.collect_session` discovers those clips by **scraping** the channel
with `yt-dlp --flat-playlist` and regex-parsing titles (`youtube_clips.py:29-55`). Scraping is
fragile (title-format dependent, unofficial, rate-limited, breaks when yt-dlp/YouTube change).
The maintainer authenticated `gcloud` (mabu.mate@gmail.com) to use the official API instead.

## Decision

We will use the **official YouTube Data API v3** for clip **discovery/metadata** — list a
session's clips per TOP via `channels.list(forHandle=bundestag)` → uploads playlist →
`playlistItems.list` (or `search.list` with `channelId` + query) — authenticated by a GCP API key
(`YOUTUBE_API_KEY` in `.env`, gitignored). A new module `pipeline/youtube_api.py` implements
this, mirroring the `collect_session` output shape so the ingestion flow is interchangeable.

**yt-dlp remains** for the auto-**caption text**: the Data API `captions.download` only works for
videos you own, so others' auto-captions still come via yt-dlp (`youtube_clips._caption`). The
resulting graph stays a separate, source-tagged `yt_<wp>_<nr>` graph with per-clip video
deep-links; persons stay global (ADR-0008). LLM access/keys follow the on-prem-capable, env-based
pattern (ADR-0010); the API key is never committed and is guarded by `settings.json` + the
PreToolUse hook.

## Consequences

- Robust, official, quota-managed discovery; no dependence on title-scraping heuristics.
- Adds an external dependency on a Google API + a per-project quota (default 10k units/day);
  the API must be enabled on the GCP project and a key created.
- Two discovery backends coexist (Data API + yt-dlp scraper) — keep both behind the same
  `collect_session`-shaped interface so callers don't care which ran.
- Captions still come from yt-dlp → caption availability/quality is unchanged.

## Alternatives considered

- **Keep yt-dlp scraping only** — rejected: fragile and unofficial; the maintainer chose the
  official API.
- **Data API for captions too** — rejected: `captions.download` requires video ownership; can't
  fetch @bundestag auto-captions.
- **OAuth instead of an API key** — rejected for now: public read needs only an API key; OAuth
  adds a consent flow without benefit here.
