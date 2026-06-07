# Echte Bundestagssitzungen in Neo4j (localhost)

Drei aktuelle Sitzungen werden **vollständig** und **kollisionsfrei** in ein lokales Neo4j
geladen und **automatisch geprüft**. Reiner Localhost-Workflow (kein Cloud, keine Pages).

## Die 3 realen Szenarien (letzte Sitzungen, WP 21)

| Sitzung | Datum | TOPs | Reden | Saalreaktionen | XML |
| ------- | ----- | ---- | ----- | -------------- | --- |
| **79** | 20.05.2026 | 7 | 174 | 624 | `data/real/plenarprotokoll-21-079.xml` |
| **80** | 21.05.2026 | 23 | 174 + 16 schriftl. | 1715 | `data/real/plenarprotokoll-21-080.xml` |
| **81** | 22.05.2026 | 7 | 85 | 890 | `data/real/plenarprotokoll-21-081.xml` |

Quelle: Bundestag Open Data (gemeinfrei, § 5 UrhG), gefunden über die Plenarprotokoll-Liste
`…/ajax/filterlist/de/services/opendata/1058442-1058442` → `…/resource/blob/<id>/210NN.xml`.

## Setup (localhost)

`7474/7687` können auf der Maschine schon belegt sein (hier: ein **fremdes** Neo4j eines
anderen Projekts mit ~114k Knoten — wird NICHT angefasst). Darum läuft graph-protokoll
**isoliert auf eigenen Ports**:

```bash
# Eigene, leere Neo4j-Instanz auf 7475/7688 (eigener Container + eigenes Volume):
NEO4J_HTTP_PORT=7475 NEO4J_BOLT_PORT=7688 docker compose -f docker-compose.neo4j.yml up -d
export NEO4J_URI=bolt://localhost:7688        # neo4j / healthdataspace

# 1) Alle 3 Sitzungen vollständig laden (idempotent; Faktencheck AUS):
python scripts/load_real_sessions.py          # oder: --dry-run (nur zählen)

# 2) Automatisch prüfen (3 Szenarien, Exit 0 = alles bestanden):
python scripts/verify_neo4j.py

# Browser: http://localhost:7475   (Cypher ausprobieren)
```

Ergebnis: **3 Sitzungen · 5 601 Knoten · 14 438 Beziehungen**. (Knoten < Summe der
Einzelsitzungen, weil `Person`/`Fraktion` **sitzungsübergreifend verschmolzen** werden.)

## Wie das kollisionsfreie Laden funktioniert

Beim Bauen je Sitzung heißen Knoten lokal `top_1`, `segment_0`, … — über mehrere Sitzungen
würden diese **kollidieren**. `neo4j_loader.namespace_graph(graph, sitzung_id)` löst das:

- **sitzungsspezifisch** (TOP, Redebeitrag, Aussage, Transkriptsegment, AkustischesEreignis, …)
  → ID wird mit der Sitzungs-ID präfixt (`sitzung_bt_21_81::segment_0`).
- **global/geteilt** (`Person`, `Fraktion`, `Norm`, `Quelle`, siehe `SHARED_TYPES`)
  → ID bleibt gleich → `MERGE` verschmilzt sie über Sitzungen zu **einem** Knoten.

Genau das macht sitzungsübergreifende Fragen möglich („in welchen Sitzungen sprach Person X?").
Der Loader nutzt `factchecks=None` → **keine** `Faktencheck`/`Quelle`-Knoten über reale Personen.

## Was `verify_neo4j.py` automatisch prüft

1. **Vollständigkeit & Provenienz** — jede Sitzung hat TOPs + Reden; **jeder** Redebeitrag ist
   per `BELEGT_DURCH → Transkriptsegment` belegt; **0** Faktencheck-Verdikte über reale Personen.
2. **Saalreaktions-Analyse** — Beifall/Zwischenrufe je Typ und je gebender Fraktion über alle
   Sitzungen (z. B. Beifall 1861, Zwischenruf 355 …).
3. **Sitzungsübergreifende Personen** — Abgeordnete, die in ALLEN 3 Sitzungen sprachen
   (geteilte `Person`-Knoten; z. B. Doris Achelwilm, Caren Lay …), bei 261 Personen gesamt.

## Beispiel-Cypher (reale Cases im Neo4j-Browser, :7475)

```cypher
// Wer bekam den meisten Beifall? (Reaktion auf die Rede welcher Fraktion)
MATCH (f:Fraktion)<-[:MITGLIED_VON]-(p:Person)-[:HAT_REDEBEITRAG]->(r:Redebeitrag)
MATCH (r)<-[:REAKTION_AUF]-(e:AkustischesEreignis {subtype:'Beifall'})
RETURN f.label AS fraktion, count(e) AS beifall ORDER BY beifall DESC;

// Vom Zitat zur Quelle: eine Aussage und ihr belegendes Transkriptsegment
MATCH (a:Aussage)-[:BELEGT_DURCH]->(seg:Transkriptsegment)
RETURN a.text, seg.sprecher, seg.text LIMIT 5;

// Sitzungsübergreifend: Reden je Abgeordneter über alle geladenen Sitzungen
MATCH (p:Person)-[:HAT_REDEBEITRAG]->(:Redebeitrag)-[:ZU_TOP]->(:Tagesordnungspunkt)<-[:HAT_TOP]-(s:Sitzung)
RETURN p.label, count(DISTINCT s) AS sitzungen, count(*) AS reden ORDER BY reden DESC LIMIT 10;
```

## Natürliche Sprache (optional)

Derselbe Graph ist über **Text2Cypher** (`pipeline/neo4j_graphrag.py`) auch in natürlicher
Sprache abfragbar, sobald ein lokales LLM erreichbar ist:

```bash
NEO4J_URI=bolt://localhost:7688 \
python -m pipeline.neo4j_graphrag "Wer sprach in allen drei Sitzungen — mit wie vielen Reden?"
# benötigt einen lokalen OpenAI-kompatiblen Endpoint (Ollama/vLLM); on-prem, kein Cloud-Versand.
```

> Hinweis: Die 3 XML (~3 MB) liegen unter `data/real/` und sind gemeinfrei. Dies ist der
> **Localhost-Entwicklungsstand** — noch nicht in den Pages-Demo/CI integriert.

---

## GenAI-Stack für Genauigkeit & Performance (GraphRAG · GDS · Haystack)

LLM-Zugang über `.env` (OpenAI-kompatibel; hier **Azure AI Foundry** — `Mistral-Large-3` und
`Kimi-K2.6`, gefunden via `az cognitiveservices account deployment list`). Setup:

```bash
.venv/bin/pip install -r requirements-genai.txt        # neo4j-graphrag, graphdatascience, haystack…
cp .env.example .env                                    # Endpoint + Key eintragen (NICHT committen)
```

### 1) GraphRAG-Text2Cypher — Modellvergleich (`scripts/graphrag_compare.py`)

NL-Frage → (LLM) Cypher → Neo4j → Antwort, über die offizielle `neo4j-graphrag`-Bibliothek.
Beide Modelle erzeugen valides Cypher gegen denselben Schema-/Few-Shot-Prompt:

| Frage | Mistral-Large-3 | Kimi-K2.6 |
| ----- | --------------- | --------- |
| Wer sprach in allen 3 Sitzungen (Top 5)? | Cypher korrekt; Synthese ließ Achelwilm/Lay (4 Reden) versehentlich aus | Cypher korrekt; **Rangliste vollständig & korrekt** |
| Saalreaktionen je Sitzung? | 624 / 1715 / 890 ✓ | 624 / 1715 / 890 ✓ |
| Fraktion mit meistem Beifall? | CDU/CSU (435) ✓ | CDU/CSU ✓ |
| Laufzeit (typisch) | **~2–4 s** | ~5–18 s (Reasoning-Modell; mehr `max_tokens` nötig) |

Fazit: **Mistral-Large-3** ist deutlich schneller; **Kimi-K2.6** denkt sichtbar (`reasoning_content`)
und war bei der Synthese komplexer Ranglisten präziser. Cypher-Genauigkeit war bei beiden hoch.

### 2) Graph Data Science (`scripts/gds_analysis.py`)

GDS-Plugin im Neo4j (`docker-compose.neo4j.yml`). Projektion „Mitsprache-Graph" (261 Abgeordnete,
2342 Kanten; verbunden, wenn unter demselben TOP gesprochen):

- **PageRank** → zentralste Sprecher (z. B. Luke Hoß, Hakan Demir …).
- **Degree** → meiste Mitsprache-Partner (z. B. Lars Klingbeil, Michael Kellner …).
- **Louvain** → 17 Sprecher-Communities (Themen-/Fraktions-Cluster).

### 3) Haystack ↔ Neo4j (`scripts/haystack_neo4j.py`)

RAG-Pipeline `Neo4jDynamicDocumentRetriever` (Neo4j-Volltextindex über Transkriptsegmente) →
`PromptBuilder` → `OpenAIGenerator` (Azure Mistral). Liefert eine **belegte** Antwort mit
Sprecher-Zitaten direkt aus den echten Reden — komplementär zum strukturierten Text2Cypher.

> Reale Namen/Zitate erscheinen hier **wörtlich** aus den gemeinfreien Protokollen und sind
> **grounded** (Retrieval, keine Halluzination, keine Wertung) — kein automatischer Faktencheck.

### 4) Vektor-/Semantik-Suche (`scripts/vector_search.py`)

Embedding-Modell war im Azure-Resource nicht vorhanden → per `az cognitiveservices account
deployment create` bereitgestellt (**`text-embedding-3-large`**, 3072d, multilingual; Mistral-Embed
ist im swedencentral-Katalog nicht verfügbar). Ablauf (idempotent): Transkriptsegmente embedden →
`embedding`-Property → **nativer Neo4j-Vektor-Index** (Cosine) → `VectorCypherRetriever`
(neo4j-graphrag) zieht die bedeutungsähnlichsten Redepassagen, Mistral synthetisiert mit
Sprecher-/Sitzungsbeleg. Liefert Treffer auch ohne Stichwort-Übereinstimmung (z. B. „wirtschaftliche
Lage" → €500-Mrd.-Sondervermögen, Deutschlandfonds).

**Drei Retrieval-Wege über denselben Graphen** — je nach Frage:
strukturiert (Text2Cypher, Aggregation/Beziehungen) · stichwortbasiert (Haystack-Volltext) ·
semantisch (Vektor/Embeddings).
