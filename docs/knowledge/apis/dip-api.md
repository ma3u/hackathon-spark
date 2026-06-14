---
type: api
title: DIP-API
description: Bundestag Dokumentations- und Informationssystem — Vorgänge, persons, Drucksachen, metadata.
resource: scripts/dip_person_ids.py
tags: [api, dip, bundestag, key, metadata]
timestamp: 2026-06-14
---

# DIP-API

Parliamentary materials & official person identities.

- **Auth:** `DIP_API_KEY` (env; never commit). REST/JSON.
- **Uses:** official `dip_id` person identity + profile deep-link
  (`scripts/dip_person_ids.py`, 97% resolved); fact-check retrieval evidence
  (`factcheck_with_retrieval`); session fetch (`scripts/fetch-session.sh`).
- **landed status:** person IDs are in the graph; raw DIP Vorgänge/Drucksachen are **not yet**
  imported as nodes (`README.md` mapping row 10 — ⬜).

**Source:** `README.md:269`; `.claude/rules/api-conventions.md §6`; `docs/quellen.md`. Related:
[[faktencheck-quelle]], entity resolution.
