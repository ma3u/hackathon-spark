---
description: Pre-deploy validation — run the dep-free builds CI runs before publishing Pages
allowed-tools: Bash(python3 run_demo.py:*), Bash(python3 ingest_bundestag.py:*), Bash(python3 compare_protocol_video.py:*), Bash(git status:*), Read, Glob
---

Pre-deploy gate for **graph-protokoll**. The GitHub Pages workflow
(`.github/workflows/pages.yml`) runs `python3 run_demo.py --no-queries` on push to `main` and
publishes `web/`. Validate that build here **before** committing/pushing.

## Build (exactly what gets deployed — must succeed on stdlib only)

Audio demo → regenerates `web/data/*.json` (the data Pages serves):
!`python3 run_demo.py --no-queries`

Official-XML path → regenerates `bundestag_xml*.json` + dashboard + accessible text:
!`python3 ingest_bundestag.py`

Gap-analysis self-test (sanity on the metrics tooling):
!`python3 compare_protocol_video.py`

Resulting working-tree changes:
!`git status --short`

## Verdict — report PASS/FAIL on each, then an overall go/no-go

1. **Builds clean.** Both `run_demo.py --no-queries` and `ingest_bundestag.py` exit 0 with no
   traceback and no `ModuleNotFoundError` — proves the demo path is still dependency-free
   (the #1 deploy risk). The fact-check `assert` in `factcheck.py` did not fire.
2. **Artifacts present & non-empty.** Confirm `web/data/` now contains `gemeinderat.json`,
   `bundestag.json`, `bundestag_xml.json`, the matching `*_dashboard.json`, and
   `*_barrierefrei.txt`. These are tracked and shipped — `web/data/` must not be empty.
3. **Frontend can read them.** `web/index.html` fetches `data/<scenario>.json` and
   `data/<scenario>_dashboard.json`; the regenerated files keep the SPARK keys
   (`nodes/relationships`, `id/label/type/subtype/schicht`). Spot-check one.
4. **Self-test sane.** `compare_protocol_video.py` printed a WER, a Saalreaktions-Recall, and
   a non-error Bewertung block.
5. **Diff is intended.** The only changes should be regenerated `web/data/*` (and gitignored
   `output/*`). Flag anything else.

If all pass: report ready to commit & push (Pages will redeploy). If any fail: stop, name the
failing step and the fix — do **not** recommend pushing.
