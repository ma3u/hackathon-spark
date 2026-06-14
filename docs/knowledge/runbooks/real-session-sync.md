---
type: runbook
title: Real-session sync
description: Fetch + ingest official Bundestag sessions into the graph.
resource: scripts/sync_sessions.py
tags: [runbook, real-data, ingestion, bundestag]
timestamp: 2026-06-14
---

# Runbook — real-session sync

Real data is real & gemeinfrei (`data/real/`); fact-check on real persons is LLM + disclaimer
(ADR-0007), never the fictional corpus.

```bash
# Shipped real session (no auto-verdicts):
python ingest_bundestag.py --xml data/real/plenarprotokoll-20-214.xml \
    --name bundestag_real --no-factcheck

# Pull official sources for a session (runs on YOUR machine):
./scripts/fetch-session.sh 21 81            # Open-Data XML + DIP-API + YouTube

# Incremental, idempotent import (skips existing):
python scripts/sync_sessions.py --official --from 1 --to 81 --load   # amtliches XML (amt_)
python scripts/sync_sessions.py --youtube --load                     # YouTube streams (yt_)
python scripts/sync_sessions.py --gap                                # WER / reaction-recall
```

Two source-tagged graphs per session (`amt_` / `yt_`), global persons (ADR-0008). Needs Neo4j up
([[neo4j-load]]).

**Source:** `CLAUDE.md` Build section; `README.md:272-277`. Skill: `bundestag-ingestion`.
