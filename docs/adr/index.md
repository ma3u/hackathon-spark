# Architecture Decision Records

Nygard-style, immutable. To change a decision, add a new ADR that supersedes the old one — never
edit an Accepted ADR's Decision. New ADRs start from [`0000-template.md`](0000-template.md).

| ADR | Title | Status |
| --- | ----- | ------ |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-graphrag-over-vector-rag.md) | Neo4j knowledge graph + GraphRAG, not vector-RAG alone | Accepted |
| [0003](0003-spark-graph-format-contract.md) | SPARK graph format as a cross-project contract | Accepted |
| [0004](0004-dual-path-stdlib-demo.md) | Dual-path modules with a stdlib-only demo path | Accepted |
| [0005](0005-audio-second-provenance.md) | Mandatory audio-second provenance (BELEGT_DURCH) | Accepted |
| [0006](0006-factcheck-always-has-source.md) | Every FactCheck carries a Quelle; unbelegt ≠ falsch | Accepted |
| [0007](0007-llm-verdicts-real-persons-disclaimer.md) | Real-person fact-checks: captioned AI suggestion + human-in-the-loop | Accepted (supersedes `--no-factcheck`) |
| [0008](0008-two-graphs-per-session-namespaces.md) | Two source-tagged graphs per session, global persons | Accepted |
| [0009](0009-parameterized-cypher-safe-gating.md) | Parameterized Cypher with `_SAFE` gating | Accepted |
| [0010](0010-on-prem-llm-openai-compatible.md) | On-prem-capable LLM via OpenAI-compatible endpoint | Accepted |
| [0011](0011-eupl-public-money-public-code.md) | License under EUPL-1.2 (Public Money – Public Code) | Accepted |
| [0012](0012-five-layer-ontology-schicht.md) | Five-layer ontology in a `schicht` property | Accepted |
| [0013](0013-youtube-data-api-discovery.md) | YouTube clip discovery via the official Data API v3 (yt-dlp keeps captions) | Accepted |
| [0014](0014-spark-reuse-temporal-litellm.md) | SPARK reuse: Temporal + LiteLLM; keep Haystack; no Docling/MinIO | Accepted |
| [0015](0015-llm-provider-independence.md) | LLM provider independence (OpenAI-compat boundary · on-prem · embedding swap-safety) | Accepted |
| [0016](0016-design-system-material-bundestag.md) | Design system: Material Design + Bundestag corporate look | Proposed |

Each ADR cites the repo source(s) it is grounded in. Structural ADRs link a diagram in
[`../diagrams/`](../diagrams/).
