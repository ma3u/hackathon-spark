---
type: datamodel
title: Protocol
description: The central data class both the audio and XML fronts produce; everything downstream consumes it.
resource: pipeline/extract.py
tags: [datamodel, protocol, contract]
timestamp: 2026-06-14
---

# Protocol

The convergence point of the two input fronts (audio `align` and `bundestag_xml`). A `@dataclass`
with these lists, all consumed downstream:

`meeting{}`, `tops[]`, `antraege[]`, `abstimmungen[]`, `beschluesse[]`, `befangenheiten[]`,
`aufgaben[]`, `redebeitraege[]`, `aussagen[]`, `fragen[]`, `kommentare[]`, `utterances[]`.

## Notes

- Every extractable record carries `quelle_utterances: list[int]` (source segment indices) →
  become `BELEGT_DURCH → Transkriptsegment` edges. See [[provenienz-belegt-durch]].
- `top_nummer: int` links records to their TOP.
- `Utterance.herkunft` ∈ `audio` | `protokoll` | `audio-SED`; `timecode` is `mm:ss` for audio,
  `"Prot."` for XML.
- The LLM extraction contract is the JSON schema in `extract.EXTRACTION_PROMPT` — keep schema
  and dataclass fields in sync.

**Source:** `pipeline/extract.py`; `.claude/rules/api-conventions.md §2`. Built into a graph by
[[spark-graph-format]].
