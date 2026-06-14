---
title: Entity resolution + DIP person IDs
status: done
owner: ma3u
updated: 2026-06-14
adr: ["0008"]
knowledge: ["docs/knowledge/datamodels/protocol.md"]
---

# Entity resolution + DIP person IDs

Merged `Person` duplicates that arose from name variants (Anrede / Titel / NBSP) and attached
official DIP identities so global person nodes don't fork across sources/sessions.

**Status:** done. Source: `docs/challenge-plan.md:46-47` (table rows 21, 21b), `:88-90`.

- String resolution: `scripts/entity_resolution.py` + `bundestag_xml._canon_person_name` —
  682 → 671 nodes (`challenge-plan.md:46`).
- DIP person IDs: `scripts/dip_person_ids.py` — 97 % resolved, official `dip_id` + profile
  deep-link, `dip_id` merge catches e.g. Inge/Ingeborg Gräßle → 668 nodes
  (`challenge-plan.md:47`).

**Verify:** E2E suite checks no duplicate persons and source correctness (`tests/`).
