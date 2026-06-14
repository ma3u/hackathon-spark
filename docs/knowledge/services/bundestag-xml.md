---
type: service
title: Bundestag-XML front
description: Parses official plenary-protocol XML directly into a Protocol (no audio needed).
resource: pipeline/bundestag_xml.py
tags: [service, xml, bundestag, saalreaktionen]
timestamp: 2026-06-14
---

# Bundestag-XML front

The second input front: parses the official `dbtplenarprotokoll` XML (DTD, WP19+) directly into
a [[protocol]] — same downstream as the audio front.

- `parse_plenarprotokoll`: reads `<sitzungsverlauf>` → `sitzungsbeginn` /
  `tagesordnungspunkt` / `zusatzpunkt` / `sitzungsende`.
- `<kommentar>` carries the official **Saalreaktionen** (Beifall/Zwischenruf/Lachen/Widerspruch)
  → `AkustischesEreignis`.
- `_ivz_titles` (TOC titles), Anlagen "zu Protokoll gegebene Reden"/§31-GO →
  `Redebeitrag(schriftlich=true)`, `_canon_person_name` (Anrede/Titel/NBSP canonicalization →
  entity resolution).
- Malformed XML → clean `ParseError` (tested in the negative E2E suite).

**Source:** `pipeline/bundestag_xml.py`; `.claude/rules/api-conventions.md §6`. Data source:
[[bundestag-opendata-xml]]. Skill: `bundestag-ingestion`.
