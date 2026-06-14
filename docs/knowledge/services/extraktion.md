---
type: service
title: Extraktion
description: Utterances → Protocol (TOPs, decisions, statements, questions).
resource: pipeline/extract.py
tags: [service, extraction, llm, produktivpfad, demopfad]
timestamp: 2026-06-14
---

# Extraktion

Builds the [[protocol]] from `Utterance`s.

- **Produktivpfad** `extract_with_llm`: local LLM (vLLM/Ollama) with a JSON-schema constraint
  (`EXTRACTION_PROMPT`). Unimplemented production functions raise `NotImplementedError` with the
  documented contract.
- **Demopfad** `extract_rule_based`: deterministic stdlib extraction.
- `extract._is_checkable` gates which `Aussage`s go to fact-check (a quantifiable figure present,
  **not** a promise like "wird … vorlegen" — those become `Aufgabe`s). See [[factcheck]].
- Keep `EXTRACTION_PROMPT` schema and the `Protocol` dataclass fields in sync.

**Source:** `pipeline/extract.py`; `.claude/rules/api-conventions.md §2`. Skill: `knowledge-graph`.
