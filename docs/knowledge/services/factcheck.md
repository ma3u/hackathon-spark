---
type: service
title: Fact-check
description: Aussage → Verdikt + Quelle (always), with audio provenance.
resource: pipeline/factcheck.py
tags: [service, factcheck, verdikt, quelle, invariant]
timestamp: 2026-06-14
---

# Fact-check

Produces a [[faktencheck-quelle]] for each checkable `Aussage`.

- **Demopfad** `factcheck_rule_based(aussagen, evidenz_path)`: deterministic keyword overlap vs.
  the **fictional** `data/evidence/evidenz.json` (≥0.6 → that verdict, else `unbelegt`). For
  fictional demo scenarios **only**.
- **Produktivpfad (real content)** `factcheck_with_llm` / `factcheck_with_retrieval`: Brave web
  search + DIP-API + Wikipedia → LLM NLI verifier, throttled `_chat_retry`. Verdicts on real
  persons carry `_LLM_DISCLAIMER` + human-in-the-loop.
- **Invariant:** `assert all(fc.quelle …)`; `unbelegt` ≠ `falsch`.

**Source:** `pipeline/factcheck.py`; ADR-0006, ADR-0007. Skill: `fact-checking`. Corrections
play back via `scripts/apply_corrections.py`.
