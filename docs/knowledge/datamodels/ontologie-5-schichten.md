---
type: datamodel
title: 5-layer ontology (schicht)
description: Semantic layering carried on every node; drives frontend coloring.
resource: pipeline/graph_build.py
tags: [datamodel, ontology, schicht]
timestamp: 2026-06-14
---

# 5-layer ontology (`schicht`)

Every node carries `schicht` ∈ {`normativ, zeitlich, prozedural, fallbezug, reaktion,
faktencheck, provenienz`}.

| Layer | Nodes | Note |
| ----- | ----- | ---- |
| normativ | `Norm` | kommunal only (no fake GemO in the Bundestag) |
| zeitlich | `Sitzung`, Fristen | |
| prozedural | `Tagesordnungspunkt → Antrag → Abstimmung → Beschluss → Aufgabe` | |
| fallbezug | `Person`, `Fraktion`, `Redebeitrag`, `Aussage`, `Frage` | |
| reaktion | `AkustischesEreignis` / Saalreaktion | Beifall/Zwischenruf/Lachen/Widerspruch |
| faktencheck | `Faktencheck`, `Quelle` | |
| provenienz | `Transkriptsegment` | [[provenienz-belegt-durch]] |

`schicht` drives `web/index.html` `LAYER` coloring (dynamic legend, only present layers).

**Source:** `pipeline/graph_build.py:6-12`; `README.md:138-147`; ADR-0012.
