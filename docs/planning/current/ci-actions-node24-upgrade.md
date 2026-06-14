---
title: "CI: upgrade GitHub Actions to Node-24-capable versions"
status: current
owner: ma3u
updated: 2026-06-14
adr: ["0004"]
knowledge: ["docs/knowledge/runbooks/publish-pages.md"]
---

# CI: upgrade GitHub Actions to Node-24-capable versions

GitHub enforces Node 24 for Actions from **2026-06-16**. The Pages workflow
(`.github/workflows/pages.yml`) must pin `actions/*` to Node-24-capable versions so the dep-free
build + Pages deploy keep running.

**Status:** current (imminent — deadline 2026-06-16). Source: `docs/challenge-plan.md:97`
(Schritt 7, ⬜).

- Bump `actions/*@v4` (checkout / upload-pages-artifact / deploy-pages etc.) to Node-24-ready
  releases in `.github/workflows/pages.yml`.
- Keep the build dep-free (ADR-0004): the workflow still runs `python3 run_demo.py --no-queries`
  on Python 3.11 stdlib, no pip.

**Verify:** push to a branch; the Actions run is green on the new runner; Pages redeploys.
