# 0008. Two source-tagged graphs per session (amtlich vs. YouTube), global persons

- **Status:** Accepted
- **Date:** 2026-06-14 (records a decision live since real-data ingestion)
- **Deciders:** maintainer (ma3u)
- **Source(s):** `README.md:247-277`; `scripts/sync_sessions.py`;
  `docs/spark-und-echtdaten.md`; `docs/neo4j-echtsitzungen.md`
- **Diagram:** [`docs/diagrams/two-graphs-namespaces.mmd`](../diagrams/two-graphs-namespaces.mmd)

## Context

A Bundestag session has two very different sources: the **amtliches XML** (stable, official,
with annotated Saalreaktionen, from `dserver.bundestag.de`) and the **YouTube Gesamtmitschnitt**
(auto-captions, no speaker labels, decays over time — only ~recent streams available). Merging
them into one graph would blur provenance and make the WER/recall delta between sources
unmeasurable.

## Decision

We will keep **two separate, source-tagged graphs per session**, distinguished by
`metadata.herkunft` (`amtlich` / `youtube`) and namespaced IDs (`amt_<wp>_<nr>` vs.
`yt_<wp>_<nr>`). `Person` and `Fraktion` nodes stay **global** (un-namespaced) so the same human
appears in both graphs and across sessions. The official graph fuses the amtliches XML with a
Mediathek video deep-link per speech (`Redebeitrag.video_url`); YouTube is a separate graph.
Incremental, idempotent import via `scripts/sync_sessions.py`; the delta is quantified by
`--gap` (WER, reaction-recall).

## Consequences

- Cross-session queries work ("in welchen Sitzungen sprach Person X?"); per-source provenance
  stays clean.
- Enables a hybrid workflow: near-real-time YouTube + golden-standard XML.
- Person de-duplication across sources becomes essential → ADR handled by entity resolution
  (`scripts/entity_resolution.py`, DIP-IDs) so global nodes don't fork on name variants.

## Alternatives considered

- **One merged graph per session** — rejected: loses source provenance and the measurable
  source delta.
- **Namespacing persons too** — rejected: would fork the same human per source/session, breaking
  cross-session analytics (GDS Mitsprache-Graph).
