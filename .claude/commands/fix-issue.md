---
description: Investigate a GitHub issue and produce a grounded fix plan for graph-protokoll
argument-hint: <issue-number>
allowed-tools: Bash(gh issue view:*), Bash(git log:*), Bash(git grep:*), Read, Grep, Glob
---

You are investigating GitHub issue **#$ARGUMENTS** for **graph-protokoll**.

## Issue

!`gh issue view $ARGUMENTS`

## Workflow

1. **Understand** the issue. Restate it in one sentence and decide which part of the pipeline
   it touches: audio (`asr`/`diarize`/`align`/`sound_events`/`subtitles`), extraction
   (`extract`/`bundestag_xml`), graph (`graph_build`/`export`/`neo4j_loader`), fact-check
   (`factcheck`), querying (`graphrag`/`neo4j_graphrag`), outputs (`dashboard`/`accessible`/
   `gap_analysis`), web (`web/index.html`), or scripts/CI.
2. **Reproduce / locate.** Find the relevant code with Grep/Glob and read it. If it's
   behavioral, reproduce via the dep-free path (`python3 run_demo.py`,
   `python3 ingest_bundestag.py`, `python3 compare_protocol_video.py`). Quote the exact
   file:line where the problem lives.
3. **Diagnose** the root cause — not just the symptom. Note which Produktivpfad vs Demopfad is
   involved.
4. **Propose a fix** that respects the project invariants (read `.claude/rules/*.md` and
   `CLAUDE.md`): stdlib-only demo stays dep-free; fact-check keeps its `quelle`; provenance
   edges preserved; SPARK format keys unchanged; Cypher stays parameterized; German +
   dual-path conventions kept; demo data stays fictional.
5. **Plan**, don't blindly edit. Output: root cause, the minimal change set (files + what
   changes), how to verify (which demo/self-test to run + expected result), and any risk or
   open question to confirm with the maintainer first.

If `$ARGUMENTS` is empty or the issue can't be fetched, say so and ask for the issue number.
