---
type: log
title: knowledge base change log
description: Dated history of changes to the OKF knowledge bundle.
timestamp: 2026-06-14
tags: [okf, log]
---

# Knowledge base — change log

- **2026-06-14** — Bundle created (control-stack generation). Initial concepts for datamodels,
  services, apis, runbooks; decisions level points to ADRs 0001–0012. Grounded in the repo as of
  commit `603f3d9` and `docs/challenge-plan.md` (Stand 2026-06-12). Gaps marked `UNKNOWN`.
- **2026-06-14** — Added generated `datamodels/graph-schema.md` (Meta-Graph) +
  `docs/diagrams/graph-meta-schema.mmd` via `scripts/graph_schema.py` (introspects
  `web/data/*.json`: 16 node types, 21 rel types, 18 metadata fields). Surfaced a `schicht`
  drift on `AkustischesEreignis` (fallbezug vs. reaktion) to fix later.
