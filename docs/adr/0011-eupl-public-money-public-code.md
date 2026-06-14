# 0011. License under EUPL-1.2 (Public Money – Public Code)

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since project start)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `LICENSE`; `publiccode.yml`; `NOTICE.md`; `README.md:406-412`;
  `scripts/publish-to-github.sh`

## Context

`graph-protokoll` is a public-sector prototype for the BMDS SPARK Hackathon. The reference
solution **SPARK Workflow** is EUPL-1.2 under the "Public Money – Public Code" principle.
Publicly funded code should be publicly reusable, and license compatibility with SPARK matters.

## Decision

The project is licensed **EUPL-1.2**. Machine-readable metadata lives in `publiccode.yml`;
attribution in `NOTICE.md`. The authoritative EUPL full text is fetched at publish time by
`scripts/publish-to-github.sh` (or manually from the EU joinup portal). New dependencies must be
license-compatible with EUPL-1.2.

## Consequences

- Forks/derivatives inherit EUPL obligations; aligns with German PMPC policy and SPARK.
- A dependency with an incompatible license is a blocker (compliance review checks this).
- Distribution carries the official EUPL notice.

## Alternatives considered

- **MIT/Apache-2.0** — rejected: weaker copyleft, and diverges from the SPARK reference license.
- **Proprietary / no license** — rejected: contradicts Public Money – Public Code.
