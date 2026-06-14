---
title: Mediathek video deep-links on all 81 sessions
status: done
owner: ma3u
updated: 2026-06-14
adr: ["0008"]
knowledge: ["docs/knowledge/apis/youtube-mediathek.md"]
---

# Mediathek video deep-links on all 81 sessions

Each speech in the official graph carries a Bundestag-Mediathek video deep-link
(`Redebeitrag.video_url`), so the official source = amtliches XML + per-speech video.

**Status:** done. Source: `docs/challenge-plan.md:38` (Schritt 4), README "Stand".

- `scripts/mediathek_links.py`: 81/81 sessions with a 📺 Mediathek deep-link; **7388 Reden**
  speaker-accurately linked, in Neo4j and on Pages (`challenge-plan.md:38`).
- The official, per-session graph fuses XML + Mediathek (one official graph); YouTube remains a
  separate graph (ADR-0008).
