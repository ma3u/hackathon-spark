---
title: Mensch-im-Loop correction/release (M4) + a11y audit
status: done
owner: ma3u
updated: 2026-06-14
adr: ["0007"]
knowledge: ["docs/knowledge/services/factcheck.md"]
---

# Mensch-im-Loop correction/release (M4) + a11y audit

A human can approve / reject / correct each AI fact-check before publication, and corrections
are played back into Neo4j and the Pages data. Accessibility of the Pages app was audited.

**Status:** done. Source: `docs/challenge-plan.md:45` (table row 20), `:90` (Schritt 5);
recent commits `610d4c4`, `755e7f4` (M4) and `b7947d9`, `a3c6cfa` (a11y audit).

- UI review (freigeben/ablehnen/korrigieren), persisted to localStorage + export.
- `scripts/apply_corrections.py` plays corrections back to Neo4j / Pages, keeping `Quelle` +
  the KI-Verdikt.
- Barrierefreiheit-Audit of the Pages app (axe-core: 3 → 0 violations).

Implements the human-in-the-loop default of ADR-0007 (no auto-published verdicts on real
persons).
