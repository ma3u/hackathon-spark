---
description: Python coding conventions for graph-protokoll source (pipeline + entry points)
globs:
  - "pipeline/**/*.py"
  - "run_demo.py"
  - "ingest_bundestag.py"
  - "compare_protocol_video.py"
  - "scripts/*.py"
alwaysApply: false
---

# Code style — graph-protokoll

Conventions extracted from the existing `pipeline/` modules. Match them; there is no
auto-formatter or linter config, so consistency is by hand.

## Module skeleton

Every module looks like this:

```python
"""
<Concern> — <one-line purpose in German>.

Produktivpfad: <the real/heavy approach — Whisper, pyannote, Neo4j, LLM, …>.
Demopfad: <the stdlib, deterministic, dep-free fallback used in the demos>.
"""

from __future__ import annotations   # ALWAYS the first import

import json                          # stdlib first
from dataclasses import dataclass
from pathlib import Path

from .align import Utterance         # local imports last, relative within pipeline/
```

- `from __future__ import annotations` is mandatory and goes first.
- The docstring is **German** and explicitly names the **Produktivpfad** and **Demopfad**.

## Dual-path rule (the core pattern)

Each capability has a heavy production function and a light demo function:

| Production (heavy) | Demo (stdlib, deterministic) |
| ------------------ | ---------------------------- |
| `asr.transcribe` | `asr.load_pretranscribed` |
| `align.align` | `align.from_pretranscribed` |
| `extract.extract_with_llm` | `extract.extract_rule_based` |
| `factcheck.factcheck_with_retrieval` | `factcheck.factcheck_rule_based` |
| `sound_events.detect_events` | `sound_events.load_events` |
| `neo4j_graphrag` (Text2Cypher) | `graphrag.GraphRAG` (intent router) |

- Production-only functions that aren't implemented **raise `NotImplementedError`** with a
  docstring that documents the real contract (see `extract.extract_with_llm`). Don't stub
  them silently.
- **Heavy deps are lazy-imported inside the function**, marked `# lazy`:
  ```python
  def transcribe(...):
      from faster_whisper import WhisperModel  # lazy: nur im Produktivpfad importiert
  ```
  Heavy deps: `faster_whisper`, `pyannote`, `torch`, `whisperx`, `neo4j`, `neo4j_graphrag`,
  `librosa`, `numpy`, `panns_inference`, `openai`. **Never** import these at module top —
  it would break the stdlib-only demo.

## Naming & language

- **German** for domain identifiers and user-facing strings: `Beschluss`, `Abstimmung`,
  `Befangenheit`, `Aufgabe`, `Redebeitrag`, `Aussage`, `Faktencheck`, `Quelle`, `kommentare`,
  `beschlussfaehig`, `quelle_utterances`. English for generic plumbing (`node`, `rel`,
  `build`, `export`, `score`).
- Private helpers are prefixed `_`: `_slug`, `_search`, `_count_before`, `_flush`, `_norm`,
  `_props`, `_classify_kommentar`.
- Module-level constants are `UPPER_SNAKE`: `EXTRACTION_PROMPT`, `VERDIKTE`, `AUDIOSET_MAP`,
  `NEO4J_SCHEMA`, `POSITIV`, `NEGATIV`, `_KOMMENTAR_TYP`.

## Types, dataclasses, functions

- 3.10+ type syntax: `str | None`, `list[dict]`, `int | None`, `dict[str, dict]`.
- Structured records are `@dataclass` (`Word`, `AsrResult`, `SpeakerTurn`, `Utterance`,
  `Protocol`, `FactCheck`); mutable defaults use `field(default_factory=list)`.
- Loose intermediate records are plain `dict`s keyed by the JSON field names used downstream —
  keep those keys exact (`quelle_utterances`, `top_nummer`, `verdikt`, …).
- Public functions with several config args make them **keyword-only** with `*`:
  `def build_graph(p, *, audio_file, sitzung_id, factchecks=None)`.

## I/O, regex, formatting

- Paths via `pathlib.Path`. Read/write text with `encoding="utf-8"`.
- JSON dumps: `json.dumps(obj, ensure_ascii=False, indent=2)` (German chars stay readable).
- Reused regex is compiled at module level (`_TS`, `_NAME`, `_SAFE`); one-offs use inline
  `re.search`. Validate any value used as a Cypher label/type with `_SAFE` first.
- 4-space indent, ~100-column soft wrap, double-quoted strings.

## Comments & CLI output

- Section headers use box-drawing rules: `# ── L3: Abstimmungen ──────────`.
- Comments explain **why**, especially legal/ethical reasoning (DSGVO Art. 9 biometrics,
  provenance for Rechtsverbindlichkeit, "unbelegt ≠ falsch"). Preserve these — they encode
  requirements, not noise.
- CLI scripts use `argparse`, an `if __name__ == "__main__":` guard, and `print()` with
  emoji status markers (`🎙️ 📄 📦 ✓ ⚠ 🔊`). Keep the style when adding output.
- Enforce invariants with `assert` and a German message (see `factcheck.py`).
