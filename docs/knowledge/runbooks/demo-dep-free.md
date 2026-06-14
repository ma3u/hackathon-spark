---
type: runbook
title: Dep-free demo
description: Run the whole pipeline on Python 3.11 stdlib — the baseline smoke test.
resource: run_demo.py
tags: [runbook, demo, stdlib, ci]
timestamp: 2026-06-14
---

# Runbook — dep-free demo

No pip, GPU, network, or models. Python 3.11+ stdlib only (ADR-0004).

```bash
python3 run_demo.py                       # both scenarios (gemeinderat + bundestag)
python3 run_demo.py --scenario bundestag  # one scenario (+ fact-check)
python3 run_demo.py --no-queries          # only (re)generate web/data/*.json
python3 ingest_bundestag.py               # official-XML front → graph (dry-run Neo4j)
python3 compare_protocol_video.py         # gap-analysis self-test (WER/recall)
python3 -m http.server -d web 8000        # serve the Pages app at localhost:8000
```

**Pass = ** exit 0, no traceback, no `ModuleNotFoundError` (a leaked heavy import), the
`factcheck.py` `assert` did not fire, and demo Q&A answers carry `↳ Audiobeleg`. This is what CI
runs (`pages.yml`: `run_demo.py --no-queries`) and what `/deploy-check` validates.

**Source:** `CLAUDE.md` Build section; `.claude/rules/testing.md`.
