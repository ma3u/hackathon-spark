---
type: index
title: graph-protokoll knowledge base
description: OKF v0.1 knowledge bundle — one concept per file; the file path is the concept identity.
timestamp: 2026-06-14
tags: [okf, knowledge, index, graph-protokoll]
---

# graph-protokoll — knowledge base (OKF v0.1)

Progressive disclosure: start here, drill into a level, then a concept. Each concept file is
grounded in a repo source (`resource:` in its frontmatter). Spec:
<https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf>. Change history:
[`log.md`](log.md).

## Levels

- **[datamodels/](datamodels/index.md)** — the data contracts: `Protocol`, the SPARK graph
  format, the 5-layer ontology, `FactCheck`/`Quelle`, provenance, `Transkriptsegment`.
- **[services/](services/index.md)** — the pipeline modules and their Produktiv/Demo pairs.
- **[apis/](apis/index.md)** — external data sources & systems (Bundestag Open Data, DIP-API,
  YouTube/Mediathek, Azure AI Foundry, Neo4j).
- **[runbooks/](runbooks/index.md)** — how to run things (dep-free demo, real-session sync,
  Neo4j load, E2E tests, publish Pages).
- **[decisions/](decisions/index.md)** — pointer into the ADRs (`docs/adr/`).

## Related

- Lean operating manual: [`../../CLAUDE.md`](../../CLAUDE.md) (+ `@.claude/rules/*`).
- Live tracker: [`../challenge-plan.md`](../challenge-plan.md) · board: [`../planning/index.md`](../planning/index.md).
- Diagrams: [`../diagrams/`](../diagrams/).
