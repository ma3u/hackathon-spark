# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-06-14
- **Deciders:** maintainer (ma3u)
- **Source(s):** this control-stack generation; `CLAUDE.md`; `docs/challenge-plan.md`

## Context

`graph-protokoll` already encodes many load-bearing decisions implicitly — in `CLAUDE.md`
gotchas, the `.claude/rules/*.md`, module docstrings, and `docs/`. They were not captured as
discrete, dated, immutable records, so the *why* behind a contract (e.g. "every FactCheck has a
Quelle") is scattered and at risk of silent erosion.

## Decision

We will record architecturally significant decisions as **Nygard-style ADRs** under
`docs/adr/`, numbered sequentially from `0000-template.md`. Each ADR states Context, Decision,
Consequences, Alternatives, and cites the repo source it is grounded in. ADRs are **immutable**
once Accepted — a changed decision is a *new* ADR that supersedes the old one. Structural ADRs
link a before/after diagram in `docs/diagrams/`.

## Consequences

- The rationale behind each invariant is discoverable and durable; `/plan` opens ADR stubs for
  decisions implied by new planning items.
- A small discipline cost: significant changes must add or supersede an ADR.
- ADRs 0002–0011 retroactively capture decisions already live in the codebase, each cited.

## Alternatives considered

- **Keep decisions only in `CLAUDE.md` / docs** — rejected: no dated record, mutable, and the
  lean `CLAUDE.md` prefix should stay small (depth loads on demand).
- **Wiki / external tracker** — rejected: violates "Public Money – Public Code" co-location;
  decisions should live with the code under EUPL-1.2.
