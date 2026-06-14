# Planning board — graph-protokoll

One file per work item, flowing `future/ → current/ → done/` (the dated record is kept, not
deleted). This board **mirrors** the live human tracker
[`docs/challenge-plan.md`](../challenge-plan.md) — that file stays the source of truth; groom
this board with `/plan`. Frontmatter: `title, status, owner, updated`, optional `adr:`/
`knowledge:` links.

## ✅ done
- [Audio pipeline + SPARK graph + outputs](done/audio-pipeline-and-spark-graph.md)
- [Echtdaten: all 81 WP21 protocols in Neo4j](done/real-data-81-sessions-neo4j.md)
- [Fact-check retrieval grounding (Brave + DIP + Wikipedia)](done/factcheck-retrieval-grounding.md)
- [Entity resolution + DIP person IDs](done/entity-resolution-dip-ids.md)
- [Mediathek video deep-links on all 81 sessions](done/mediathek-deeplinks-all-81.md)
- [Mensch-im-Loop correction/release (M4) + a11y audit](done/mensch-im-loop-m4.md)
- [WER benchmark over 10 sessions](done/wer-benchmark-10-sessions.md)
- [YouTube Data API v3 integration (official clip discovery)](done/youtube-data-api-integration.md)

## 🔜 current
- [CI: upgrade GitHub Actions to Node-24-capable versions](current/ci-actions-node24-upgrade.md)

## ⬜ future
- [Bulk-ingest the 42 YouTube-confirmed stream-less sessions (clips)](future/youtube-clips-bulk-ingest.md)
- [Extend fact-check retrieval grounding to all 81 sessions](future/grounding-all-81.md)
- [Gap-diff overlay (word diff) + Diarisierungs-DER](future/gap-diff-der.md)
