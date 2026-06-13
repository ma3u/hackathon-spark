# Challenge-Plan & Fortschritt — `graph-protokoll` (SPARK Challenge 2)

Lebendiges Planungsdokument. **Challenge 2 „Da geht noch mehr!"**: neue
Verwaltungs-/Parlamentsleistung jenseits von Planung/Genehmigung —
**Plenarprotokoll/Mitschnitt → prüfbarer Knowledge Graph + Faktencheck +
Dashboard**, mit Neo4j-GraphRAG für natürliche Fragen.

Stand: **2026-06-12** · Status-Legende: ✅ fertig · 🔜 in Arbeit · ⬜ offen

## 1. Zielbild (Definition of Done)

Aus echten öffentlichen Bundestagssitzungen entsteht **automatisch**:
1. ein strukturiertes Protokoll (Reden, TOPs, Saalreaktionen, Aussagen),
2. ein **Faktencheck** prüfbarer Aussagen — **immer mit Quelle**, über reale Personen als
   KI-Vorschlag mit Disclaimer,
3. ein **Knowledge Graph in Neo4j** (Text2Cypher/GraphRAG),
4. ein **Dashboard pro Sitzung** (Redezeit, Sachthemen, Redner:innen, Sprachanteil, Feedback, Bilanz),
5. alles **on-prem/DSGVO**, mit **Provenienz** bis zur Quelle (Audiosekunde / Video-Deeplink / amtl. PDF).

## 2. Fortschritts-Tracker

| # | Baustein | Status | Artefakt |
| - | -------- | ------ | -------- |
| 1 | Audio-Pipeline (ASR→Diarisierung→Alignment) | ✅ | `pipeline/asr,diarize,align.py` |
| 2 | Extraktion + 5-Schichten-Graph (SPARK-Format) | ✅ | `pipeline/extract.py,graph_build.py` |
| 3 | Faktencheck — **immer mit Quelle** (Invariante) | ✅ | `pipeline/factcheck.py` |
| 4 | Amtliches Plenarprotokoll-XML (`dbtplenarprotokoll`) + Saalreaktionen | ✅ | `pipeline/bundestag_xml.py` |
| 5 | Neo4j-Import (idempotent, parametrisiert, namespaced) | ✅ | `pipeline/neo4j_loader.py` |
| 6 | Neo4j-GraphRAG (Text2Cypher) + GDS + Haystack + Vektor | ✅ | `pipeline/neo4j_graphrag.py`, `scripts/` |
| 7 | Sitzungs-Dashboard (Redezeit, Sachthemen, Redner, Sprachanteil, Feedback) | ✅ | `pipeline/dashboard.py` |
| 8 | Gap-Analyse YouTube ↔ amtlich (WER, Reaktions-Recall) | ✅ | `pipeline/gap_analysis.py` (79: 41 %, 81: 21 %) |
| 9 | GitHub-Pages-App (Graph + Dashboard + Protokoll-HTML) | ✅ | `web/` |
| 10 | **ECHTDATEN: alle 81 WP21-Protokolle (dserver) in Neo4j** | ✅ | `scripts/sync_sessions.py --official` |
| 11 | **YouTube-Gesamtmitschnitte** (Streams 79/81), Zeit-Deeplinks | ✅ | `--youtube`, `pipeline/subtitles.py` |
| 12 | **Bundestag-Mediathek** — korrigierte Untertitel, sprecher-attribuiert, Video je Rede | ✅ | `pipeline/mediathek.py` |
| 13 | **EIN offizieller Graph je Sitzung** = XML-Struktur + Mediathek-Video-Deeplink je Rede | ✅ | `session_ingest.ingest_official` |
| 13b | **Mediathek-Deeplinks auf ALLE 81** (81/81 Sitzungen, 7388 Reden verlinkt) | ✅ | `scripts/mediathek_links.py` |
| 14 | UI: Sitzungs-Auswahl (82) + Quellen-Umschalter 🟢 Offiziell / 🎬 YouTube, dynam. Legende | ✅ | `web/index.html` |
| 15 | **Faktencheck mit variierten Verdikten** (In-Kontext-LLM-Extraktion) | ✅ | `session_ingest.llm_factcheck_official` |
| 16 | Faktencheck-**Retrieval** (Brave-Websuche + DIP-API + Wikipedia) → Verdikt mit echter Quelle | ✅ | `factcheck.factcheck_with_retrieval` (`--retrieval`) — **70–81 grounded**, echte Quellen |
| 17 | Embeddings/Vektor-Index (Azure text-embedding-3-large) | ✅ | `scripts/vector_search.py` |
| 18 | E2E-Tests gegen reale Neo4j-Daten | ✅ | `tests/` |
| 19 | YouTube-Clips (`/videos`) als Quelle für Sitzungen ohne Stream | ⬜ | braucht **YouTube Data API Key** (`pipeline/youtube_clips.py`) |
| 20 | Korrektur-/Freigabe-Workflow (Mensch-im-Loop) | ⬜ | offen (M4) |
| 21 | **Entity-Resolution Person** (Anrede/Titel/NBSP → Merge) | ✅ | `scripts/entity_resolution.py` (682→671), `bundestag_xml._canon_person_name` |
| 21b | **DIP-Personen-IDs** (amtliche Identität + Profil-Deeplink, dip_id-Merge) | ✅ | `scripts/dip_person_ids.py` (97% aufgelöst, 668 Knoten) |

## 3. Stand 2026-06-12 (Fortschritts-Log)

- **Faktencheck-Retrieval gelöst (NEU):** Brave-Websuche als Korpus schließt die alte
  „Korpus zu allgemein"-Lücke. `factcheck_with_retrieval` = Brave + DIP-API + Wikipedia,
  LLM urteilt gegen die Belege (Drossel `_chat_retry` ~1 Call/s + Backoff). Sitzungen 78–81
  jetzt mit **variierten Verdikten + echten autoritativen Quellen** (destatis.de, tagesschau.de,
  dip.bundestag.de, bundesfinanzministerium.de, bmi.bund.de, bundesrechnungshof.de),
  ~0 „Prüfung fehlgeschlagen". Lauf via `sync_sessions.py --official --web-graph --retrieval`.
  Beispiel 81: 24 teilweise / 9 bestätigt / 5 irreführend / 2 falsch / 12 unbelegt.
- **Echtdaten komplett:** alle 81 WP21-Plenarprotokolle + WP20/214 in Neo4j
  (~136 k Knoten / ~361 k Beziehungen). Voll-Graphen in Neo4j; Pages trägt 13 Showcase-
  Struktur-Graphen (70–81 + 214) + Dashboards für alle 82 + 2 Gap-Reports.
- **Drei klar getrennte Quellen** je Sitzung: 🟢 amtliches XML (+ Mediathek-Video je Rede),
  🎬 YouTube-Gesamtmitschnitt. Mediathek in den offiziellen Graph verschmolzen.
- **Ontologie korrigiert:** Sitzung=zeitlich, Person=fallbezug, Saalreaktion=reaktion,
  Norm nur kommunal (keine Fake-GemO im Bundestag); dynamische Legende.
- **Dashboard:** Redezeit (geschätzt), Redner:innen mit Partei, Sachthemen (Keyword),
  Fraktionsnamen kanonisiert (grüner Balken).

## 4. Risiken & offene Punkte

| Risiko | Wirkung | Gegenmaßnahme |
| ------ | ------- | ------------- |
| ~~Faktencheck-Korpus zu allgemein~~ (GELÖST) | ~~Verdikte „unbelegt"~~ | ✅ **Brave-Websuche** als Korpus → echte Quellen, variierte Verdikte |
| Brave-Free-Plan-Limit / API-Kosten bei Voll-Lauf aller 81 | Rate-/Kostengrenze | Drossel `_chat_retry`; Retrieval nur Showcase; ggf. Cache |
| LLM-Verdikte ohne Retrieval = Einschätzung, nicht belegt | Fehlurteil-Risiko | Disclaimer + „unbelegt" + Mensch-im-Loop; Retrieval-Grounding |
| Korrekturrecht der Redner:innen | Goldstandard ≠ gesprochenes Wort | als Diff modellieren (Gap-Analyse), nicht „falsch" |
| ~~Personen-Dubletten (Namensvarianten)~~ (GELÖST) | ~~unscharfe Abfragen~~ | ✅ Entity-Resolution (682→671); Quelle gefixt. Offen: DIP-Personen-IDs für Namensgleiche |
| Commit-Größe (web/data ~21 MB, 13 Voll-Graphen) | Repo-Wachstum | Struktur-Projektion (ohne Segmente) bereits; ggf. Git LFS |

## 5. Nächste konkrete Schritte

1. ✅ ~~Belastbare Faktencheck-Verdikte~~ — **erledigt** via Brave-Websuche (**ganze Showcase 70–81 grounded**).
   Optional: Grounding auf alle 81 ausweiten (Brave-Free-Plan-Limit beachten).
2. ✅ ~~Entity-Resolution für `Person`~~ — **erledigt**: String-Resolution
   (`entity_resolution.py`, 682→671) + **DIP-Personen-IDs** (`dip_person_ids.py`, 97% aufgelöst,
   amtliche dip_id + Profil-Deeplink, dip_id-Merge fängt Inge/Ingeborg Gräßle etc. → 668).
3. ⬜ **YouTube Data API Key** → `youtube_clips` für Sitzungen ohne Gesamt-Stream;
   die 42 YouTube-bestätigten Sitzungen als 🎬-Quelle ingestieren.
4. ✅ ~~Mediathek-Video-Deeplinks auf alle 81~~ — **erledigt** (`scripts/mediathek_links.py`):
   81/81 Sitzungen mit 📺 Mediathek-Deeplink, 7388 Reden sprecher-genau verlinkt (Neo4j + Pages).
5. ⬜ Mensch-im-Loop-Korrektur-/Freigabeprozess (M4), Barrierefreiheit-Audit.
6. ⬜ WER/DER-Benchmark gegen mehr Sitzungen; Gap-Report in der UI ausbauen.
7. ⬜ CI: `actions/*@v4` → Node-24-fähige Versionen (GitHub erzwingt Node 24 ab 16.06.2026).
