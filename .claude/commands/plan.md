---
description: Reconcile docs/planning/ — move finished items to done/, refresh current/, groom future/, open ADR stubs for implied decisions
argument-hint: "[optional focus, e.g. 'factcheck' or a Schritt number]"
allowed-tools: Bash(git log:*), Bash(git status:*), Read, Grep, Glob, Edit, Write
---

You are grooming the planning board for **graph-protokoll** (SPARK Challenge 2).

## Ground truth

The live, human-maintained tracker is `docs/challenge-plan.md` (numbered rows + a
"Nächste konkrete Schritte" list + a risk table). The board under `docs/planning/`
mirrors it as one file per work item, flowing `future/ → current/ → done/`. ADRs live in
`docs/adr/`; the OKF knowledge bundle in `docs/knowledge/`.

Recent commits (for what actually shipped):
!`git log --oneline -20`

## Workflow

1. **Read** `docs/challenge-plan.md`, the three `docs/planning/{done,current,future}/`
   folders, and `docs/planning/index.md`. If `$ARGUMENTS` names a focus, scope to it.
2. **Reconcile against reality.** Cross-check each `current/` item against the recent
   commits and `challenge-plan.md` status (✅/🔜/⬜). For anything now finished:
   move the file to `done/`, set `status: done`, stamp `updated:` with today's date,
   and keep the dated record (do **not** delete it).
3. **Refresh `current/`** with what is genuinely in progress (e.g. the open 🔜 rows),
   and **groom `future/`**: promote the next item(s) to `current/`, prune duplicates,
   keep titles aligned with `challenge-plan.md` row labels.
4. **ADR stubs.** If a `current/`/`future/` item implies an architectural decision not
   yet recorded, create a `docs/adr/NNNN-<slug>.md` stub from `docs/adr/0000-template.md`
   (Status: Proposed) and link it from the planning item's `adr:` frontmatter.
5. **Update `docs/planning/index.md`** so the three buckets list every item.

## Output

A short summary: items moved (future→current→done), ADR stubs opened, and any mismatch
between `challenge-plan.md` and the board you couldn't auto-resolve (ask the maintainer).
Keep frontmatter intact (`title, status, owner, updated`, optional `adr:`/`knowledge:`).
Do not invent work items — every item must trace to `challenge-plan.md` or a commit.
