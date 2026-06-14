---
title: "Echtdaten: all 81 WP21 protocols in Neo4j"
status: done
owner: ma3u
updated: 2026-06-14
adr: ["0008", "0009"]
knowledge: ["docs/knowledge/runbooks/real-session-sync.md", "docs/knowledge/apis/bundestag-opendata-xml.md"]
---

# Echtdaten: all 81 WP21 protocols in Neo4j

All 81 WP21 plenary protocols + the WP20/214 showcase are loaded into local Neo4j as
source-tagged, namespaced graphs (`amt_<wp>_<nr>` / `yt_<wp>_<nr>`), with global `Person`/
`Fraktion` nodes.

**Status:** done. Source: `docs/challenge-plan.md:58-60` (Fortschritts-Log); `README.md:12-19`.

- ~136 k Knoten / ~361 k Beziehungen in Neo4j (`challenge-plan.md:58-60`).
- Pages carries 13 showcase structure-graphs (70–81 + 214) + dashboards for all 82 + 2 gap
  reports.
- Incremental, idempotent import: `python scripts/sync_sessions.py --official --from 1 --to 81
  --load`.

**Verify:** `python scripts/verify_neo4j.py` (with Neo4j up on the configured port).
