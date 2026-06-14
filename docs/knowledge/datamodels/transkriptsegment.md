---
type: datamodel
title: Transkriptsegment
description: The provenance leaf node carrying the audio-second coordinates.
resource: pipeline/graph_build.py
tags: [datamodel, provenance, transkriptsegment]
timestamp: 2026-06-14
---

# Transkriptsegment

The leaf node every provable entity points to via `BELEGT_DURCH` (see
[[provenienz-belegt-durch]]).

- Carries `start_sec` / `end_sec`, `speaker_label`, `text`, `audio_file`; `schicht = provenienz`.
- ID is pinned to the utterance index (`segment_<idx>`) so reactions and provenance line up —
  don't renumber.
- For amtliches XML the timecode is `"Prot."` (no audio second); for audio it is `mm:ss`.

**Source:** `pipeline/graph_build.py`; `.claude/rules/api-conventions.md §1-2`; ADR-0005.
