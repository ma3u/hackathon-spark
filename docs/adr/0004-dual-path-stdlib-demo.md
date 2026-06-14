# 0004. Dual-path modules with a stdlib-only demo path

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since project start)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `CLAUDE.md` gotcha #1 + "Coding conventions"; `.claude/rules/code-style.md`
  "Dual-path rule"; `.github/workflows/pages.yml`
- **Diagram:** [`docs/diagrams/pipeline-flow.mmd`](../diagrams/pipeline-flow.mmd)

## Context

The product needs heavy ML/infra (faster-whisper, pyannote, torch, neo4j, Azure SDK) for real
audio — but a hackathon demo, CI, and reviewers must be able to run the whole pipeline with
**zero setup**: no GPU, no models, no network, no pip.

## Decision

Every capability ships **two paths**: a *Produktivpfad* (heavy/real) and a *Demopfad* (stdlib,
deterministic) — e.g. `asr.transcribe` ↔ `asr.load_pretranscribed`, `factcheck_with_retrieval` ↔
`factcheck_rule_based`. Heavy dependencies are **lazy-imported inside the function** (marked
`# lazy`), never at module top. The dep-free entry points — `run_demo.py`,
`ingest_bundestag.py`, `compare_protocol_video.py` — and the CI Pages build run on Python 3.11
stdlib only. Unimplemented production functions `raise NotImplementedError` documenting the real
contract, rather than stubbing silently.

## Consequences

- CI (`pages.yml`) runs `python3 run_demo.py --no-queries` on every push with no install step;
  reproducibility is the baseline smoke test (`.claude/rules/testing.md`).
- A heavy import leaking to module top is a real regression (`ModuleNotFoundError` in the demo).
- Some duplication (two code paths per capability) — accepted as the cost of dep-free reach.

## Alternatives considered

- **Single heavy path + "just install requirements"** — rejected: breaks offline CI, raises the
  barrier to reproduce, couples the demo to GPU/model availability.
- **Mocking heavy deps in the demo** — rejected: mocks drift from reality and hide regressions.
