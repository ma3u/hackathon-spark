<!-- KI-Entwurf: erzeugt mit Azure AI Foundry (Mistral-Large-3) via .env, scripts/gen_bewerbung.py.
     Faktenbasiert; im Mensch-im-Loop nachkorrigiert (WP20→WP21; Befangenheits-Norm; Abstimmungs-Kante).
     Vor Einreichung final von Menschen prüfen. -->

# Bewerbung: graph-protokoll – SPARK Challenge 2 „Da geht noch mehr!"

## Problem & Leistung
Verwaltungs- und Parlamentsprotokolle sind unstrukturierte Textmassen mit hohem Prüf- und
Rechercheaufwand. *graph-protokoll* wandelt alle 81 Plenarprotokolle der 21. Wahlperiode
(+ WP20/214) — ~136.000 Knoten, ~361.000 Beziehungen in Neo4j — in einen **prüfbaren Knowledge
Graph** um, inkl. Faktencheck, Provenienz bis zur Audiosekunde und Dashboard. 56 Sitzungen sind
zusätzlich über die offizielle YouTube Data API v3 mit 377 Clips erschlossen.

## Lösung: graph-protokoll
- **Datenbasis**: amtliche Plenarprotokoll-XML + Transkripte (Whisper/Diarisierung) +
  YouTube-Clips (Data API v3).
- **Graph-Struktur**: Neo4j mit Entitäten (Personen, Fraktionen, TOPs, Beschlüsse, Aussagen)
  und Relationen (z. B. `FUEHRT_ZU`, `BELEGT_DURCH`, `GEPRUEFT_ALS`).
- **Retrieval**: **GraphRAG** (Text2Cypher) für strukturierte Abfragen, **Volltextsuche**
  (Haystack) und **Vektor-Suche** für semantische Ähnlichkeit — **alle drei über denselben
  Graphen**, dazu Graph-Analytik (GDS: PageRank/Louvain).
- **Provenienz**: jede Aussage/jeder Beschluss ist mit dem Transkriptsegment (`start_sec`) und
  bei amtlichen Sitzungen mit einem Mediathek-Video-Deeplink je Rede verknüpft.
- **Faktencheck**: 5-stufige Skala (bestätigt · teilweise · irreführend · falsch · unbelegt),
  **jeder Faktencheck mit Quelle** („unbelegt" ≠ „falsch"); über reale Personen ausdrücklich
  KI-Vorschlag mit Disclaimer und menschlicher Freigabe (Mensch-im-Loop).
- **On-Prem/DSGVO**: Whisper, Diarisierung und LLM im Behördennetz (Stimmen = Art. 9 DSGVO);
  Lizenz EUPL-1.2 (Public Money – Public Code).

## Warum GraphRAG besser ist als SPARKs Vektor-RAG
1. **Mehrhop-Fragen**:
   - *„Welcher Beschluss mit welchem Abstimmungsergebnis?"*
     → Pfad: `Beschluss -FUEHRT_ZU-> Abstimmung` (Ergebnis Ja/Nein/Enthaltung).
     Vektor-RAG über Textchunks kann strukturierte Beziehungspfade nicht traversieren.
   - *„Wer war bei welchem Tagesordnungspunkt befangen — nach welcher Norm?"*
     → Pfad: `Person -BEFANGEN_BEI-> TOP`, `Person -BEFANGENHEIT_NACH-> Norm`
     (z. B. GemO §18 im Gemeinderats-Szenario). Embeddings bilden solche Pfade nicht ab.
2. **Exakte Provenienz statt Chunk-Ähnlichkeit**: GraphRAG liefert **nachvollziehbare Pfade**
   (`Aussage -BELEGT_DURCH-> Transkriptsegment.start_sec`) statt unscharfer Textähnlichkeit —
   jeder Faktencheck mit Quelle und Audio-/Video-Beleg.
3. **Komplementäre Retrieval-Methoden**: derselbe Graph trägt GraphRAG, Vektor- und
   Volltextsuche sowie Graph-Analytik — das Beste aus beiden Welten.

## Verhältnis zu SPARK
*graph-protokoll* ergänzt den SPARK-Baukasten um **zwei generische Bausteine** (ASR als Eingabe,
Graph + Faktencheck mit Provenienz) — **ohne Code-Abhängigkeit**, aber mit geteilter Mission,
Lizenz (EUPL-1.2) und On-Prem-LLM-Muster.

## Fazit
*graph-protokoll* macht Gremien- und Plenarprotokolle **maschinenlesbar, prüfbar und
nachnutzbar** — mit GraphRAG als Schlüssel für strukturierte Mehrhop-Fragen und transparente
Provenienz bis zur Audiosekunde.
