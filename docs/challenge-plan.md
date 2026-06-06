# Challenge-Plan & Fortschritt — `graph-protokoll` (SPARK Challenge 2)

Lebendiges Planungsdokument. **Challenge 2 „Da geht noch mehr!"**: neue
Verwaltungs-/Parlamentsleistung jenseits von Planung/Genehmigung —
**Audiomitschnitt/Plenarprotokoll → prüfbarer Knowledge Graph + Faktencheck +
Dashboard**, mit Neo4j-GraphRAG für natürliche Fragen.

Stand: 2026-06-06 · Status-Legende: ✅ fertig · 🔜 in Arbeit · ⬜ offen

## 1. Zielbild (Definition of Done)

Aus einer öffentlichen Bundestagssitzung entsteht **automatisch**:
1. ein strukturiertes Protokoll (Reden, TOPs, Abstimmungen, Fragen, Saalreaktionen),
2. ein **Faktencheck** quantitativer Aussagen — **immer mit Quelle**,
3. ein **Knowledge Graph in Neo4j**, per **GraphRAG (Text2Cypher)** in natürlicher
   Sprache abfragbar,
4. ein **Dashboard pro Sitzung** (Top-Themen, Sprachanteil, Feedback, Bilanz),
5. alles **on-prem/DSGVO**, mit **Provenienz** bis zur Quelle/Audiosekunde.

## 2. Fortschritts-Tracker

| # | Baustein | Status | Artefakt |
| - | -------- | ------ | -------- |
| 1 | Audio-Pipeline (ASR→Diarisierung→Alignment) | ✅ | `pipeline/asr.py,diarize.py,align.py` |
| 2 | Extraktion (TOP/Beschluss/Abstimmung/Frage/Aussage) | ✅ | `pipeline/extract.py` |
| 3 | 5-Schichten-Graph (SPARK-Format) | ✅ | `pipeline/graph_build.py` |
| 4 | Faktencheck — **immer mit Quelle** (Invariante) | ✅ | `pipeline/factcheck.py` |
| 5 | Amtliches Plenarprotokoll-XML-Parser (`dbtplenarprotokoll`) | ✅ | `pipeline/bundestag_xml.py` |
| 6 | Saalreaktionen (Beifall/Zuruf/…) aus `<kommentar>` | ✅ | `AkustischesEreignis`-Knoten |
| 7 | Neo4j-Import (idempotent, parametrisiert) | ✅ | `pipeline/neo4j_loader.py` |
| 8 | **Neo4j-GraphRAG (Text2Cypher)** | ✅ | `pipeline/neo4j_graphrag.py` |
| 9 | Sitzungs-Dashboard (Themen/Sprachanteil/Feedback) | ✅ | `pipeline/dashboard.py` + Pages |
| 10 | Gap-Analyse Protokoll ↔ Video-ASR (WER, Recall) | ✅ | `pipeline/gap_analysis.py` |
| 11 | Fetch offizieller Quellen (Open Data/DIP/YouTube) | ✅ | `scripts/fetch-session.sh` |
| 12 | GitHub-Pages-App (Graph + Dashboard) | ✅ | `web/` |
| 13 | **Sound-Event-Detection** (PANNs): Beifall/Buhrufe/Lachen + Lautstärke | ✅ | `pipeline/sound_events.py` |
| 13b | Untertitel-Transkription (YouTube/Mediathek VTT/SRT) | ✅ | `pipeline/subtitles.py` |
| 14 | Echtdaten-Test 81. Sitzung (XML + Video, letzte WP) | ⬜ | braucht Netz (M1) |
| 15 | Korrektur-/Freigabe-Workflow (Mensch-im-Loop) | ⬜ | offen (M3) |
| 16 | WER/DER-Benchmark gegen Goldstandard | 🔜 | Tool steht, Daten fehlen |

## 3. Meilensteine

- **M0 — Prototyp (erreicht):** Audio- + XML-Pfad, Faktencheck, Neo4j, GraphRAG,
  Dashboard, Gap-Tool — alles lauffähig auf Beispieldaten.
- **M1 — Echtdaten (Hackathon Tag 1):** 81. Sitzung ziehen, XML→Neo4j laden,
  Dashboard erzeugen, Gap-Report Protokoll↔Video.
- **M2 — Multimodal:** PANNs-Sound-Event-Detection (Beifall/Buhrufe/Lautstärke)
  in die Pipeline; Provenienz auf Audiosekunde.
- **M3 — Workflow & Recht:** Korrektur-/Freigabeprozess, DSGVO/Barrierefreiheit,
  Akzeptanzkriterien mit den Bundestags-Kolleg:innen.
- **M4 — Pilot:** End-to-End auf mehreren Sitzungen, WER/DER-Benchmark, Übergabe.

## 4. Risiken & offene Punkte

| Risiko | Wirkung | Gegenmaßnahme |
| ------ | ------- | ------------- |
| Mediathek-/YouTube-Lizenz für Video unklar | blockiert Audio-Pfad | mit Bundestag klären (siehe Fragenkatalog) |
| Saalreaktionen nur im Protokoll, nicht im ASR | Feedback-Lücke | SED (M2) ergänzen |
| Korrekturrecht der Redner:innen | Goldstandard ≠ gesprochenes Wort | als Diff modellieren, nicht „falsch" werten |
| Diarisierung bei Zwischenrufen/Überlappung | Sprecher-Fehler | AVSR-Ergänzung, Rednerliste als Enrollment |
| LLM-Halluzination im Faktencheck | Fehlurteil | Quellenpflicht + Mensch-im-Loop + „unbelegt" |

## 5. Nächste konkrete Schritte

1. ⬜ 81. Sitzung ziehen: `./scripts/fetch-session.sh 21 81`
2. ⬜ Gap-Report erzeugen: `python compare_protocol_video.py --xml … --asr …`
3. ⬜ PANNs-SED-Stub in `pipeline/` ergänzen (M2)
4. ⬜ Fragenkatalog mit Bundestag abstimmen (`docs/fragen-bundestag.md`)
