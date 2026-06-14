---
type: runbook
title: Publish to GitHub Pages
description: Build the data and deploy the static single-file app.
resource: .github/workflows/pages.yml
tags: [runbook, pages, deploy, ci]
timestamp: 2026-06-14
---

# Runbook — publish to GitHub Pages

The Pages workflow (`.github/workflows/pages.yml`) runs `python3 run_demo.py --no-queries` on
push to `main` and publishes `web/` — dep-free (ADR-0004).

```bash
# Validate the exact build locally first (see /deploy-check):
python3 run_demo.py --no-queries          # regenerate web/data/*.json
python3 ingest_bundestag.py               # regenerate official-XML outputs
python3 -m http.server -d web 8000        # eyeball http://localhost:8000

# Standalone repo + Pages in one command (needs `gh auth login`):
./scripts/publish-to-github.sh hackathon-spark
# → https://ma3u.github.io/hackathon-spark/
```

`web/data/*.json` is tracked on purpose (the SPARK contract is visible). Heads-up: GitHub
enforces Node 24 for Actions from 2026-06-16 → see
[[../planning/current/ci-actions-node24-upgrade]].

**Source:** `README.md:170-193`; `CLAUDE.md` Build section.
