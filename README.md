# 🎙️ graph-protokoll — vom Sitzungsmitschnitt zum prüfbaren Protokoll-Graphen

**SPARK-Hackathon Challenge 2 „Da geht noch mehr!" — Prototyp.**
Eine neue Verwaltungs-/Parlamentsleistung _jenseits_ von Planungs- und
Genehmigungsverfahren: Aus dem **Audiomitschnitt** einer Gremiensitzung
(Gemeinderat, Ausschuss, **Bundestag**, Anhörung) entsteht automatisch ein
**strukturiertes, durchsuchbares, rechtssicher belegbares Protokoll** als
Knowledge Graph mit GraphRAG — inklusive **Faktencheck** politischer Aussagen.

![GraphRAG](https://img.shields.io/badge/GraphRAG-mit%20Audio--Provenienz-brightgreen) ![Faktencheck](https://img.shields.io/badge/Faktencheck-mit%20Quellen-red) ![Szenarien](https://img.shields.io/badge/Demos-Gemeinderat%20%2B%20Bundestag-blue) ![DSGVO](https://img.shields.io/badge/KI-lokal%20%2B%20DSGVO-brightgreen) ![License](https://img.shields.io/badge/license-EUPL--1.2-green)

**Drei Demo-Szenarien:** **Gemeinderat** (Beschlüsse, Abstimmungen, Befangenheit,
Aufgaben) und **Bundestag** (fiktive Plenardebatte mit Faktencheck + Frage an die
Bundesregierung) — beide fiktiv — sowie **Bundestag (echt)**: das **echte amtliche
Plenarprotokoll WP20/214** (18.03.2025, gemeinfrei §5 UrhG) mit 45 Reden und 643
amtlichen Saalreaktionen. **Beim echten Szenario ist der Faktencheck bewusst aus**
(keine automatischen Verdikte über reale Personen). SPARK-Nutzung, Echtdaten-Wege und
die Faktencheck-Grenzen: [`docs/spark-und-echtdaten.md`](docs/spark-und-echtdaten.md).
Analyse der Bundestags-Protokollierung & des Faktenchecks:
[`docs/bundestag-protokollierung-analyse.md`](docs/bundestag-protokollierung-analyse.md).

---

## Schnellstart (läuft ohne GPU, Modelle oder Netz)

```bash
python3 run_demo.py                      # beide Szenarien
python3 run_demo.py --scenario bundestag # nur Bundestag + Faktencheck
```

Die Demo verarbeitet zwei mitgelieferte, **fiktive** Mitschnitte
(Gemeinderat Musterbach; fiktive Bundestags-Plenardebatte), baut je einen Graphen
und beantwortet GraphRAG-Fragen — **jede Antwort mit Audio-Zeitstempel als Beleg**.
Pro Szenario landen Artefakte in `output/` (SPARK-Datenformat) und in `web/data/`
(für GitHub Pages):

| Datei (`<scenario>` = gemeinderat \| bundestag) | Zweck                       |
| ----------------------------------------------- | --------------------------- |
| `<scenario>_graph_data.json`                    | Graph (`{metadata, nodes, relationships}`) |
| `<scenario>_nodes.csv` / `_relationships.csv`   | Neo4j-Bulk-Import           |
| `<scenario>_neo4j_import.cypher`                 | Idempotenter `MERGE`-Import |

Echtes Audio:

```bash
pip install -r requirements.txt
python3 run_demo.py --audio pfad/zur/sitzung.mp3
```

---

## Wie analysiert man Audio? (die Pipeline)

```
  🎙️ Audio (mp3/wav)
        │
        ▼
  ┌─────────────┐   faster-whisper large-v3, language="de", word_timestamps,
  │  ASR        │   VAD-Filter (Stille/Applaus raus)            → Wörter + Zeiten
  └─────────────┘   pipeline/asr.py
        │
        ▼
  ┌─────────────┐   pyannote/speaker-diarization-3.1
  │ Diarisierung│   "wer spricht wann?"                          → Sprecher-Turns
  └─────────────┘   pipeline/diarize.py
        │
        ▼
  ┌─────────────┐   WhisperX forced alignment: jedes Wort dem
  │ Alignment   │   überlappenden Sprecher-Turn zuordnen, zu     → Utterances
  └─────────────┘   Redebeiträgen bündeln   pipeline/align.py    (Sprecher+Text+Zeit)
        │           Sprecher-Label → Person via Enrollment/Rednerliste
        ▼
  ┌─────────────┐   Lokales LLM (vLLM/Ollama), JSON-Schema-Constraint:
  │ Extraktion  │   TOPs · Anträge · Abstimmungen · Beschlüsse · → Protocol
  └─────────────┘   Befangenheiten · Aufgaben   pipeline/extract.py
        │           jede Aussage trägt ihre Quell-Segment-Indizes
        ▼
  ┌─────────────┐   Vier-Schichten-Ontologie + Provenienzkanten
  │ Graph       │   pipeline/graph_build.py                      → Neo4j-Graph
  └─────────────┘
        │
        ▼
  ┌─────────────┐   Mehrhop-Abfragen mit Audio-Beleg
  │ GraphRAG    │   pipeline/graphrag.py                         → Antworten + Zitate
  └─────────────┘
```

**Drei Audio-spezifische Knackpunkte** (Hackathon-relevant):

1. **Diarisierung ≠ Identifikation.** pyannote liefert anonyme Labels
   (`SPEAKER_00…`). Die Zuordnung zu echten Personen kommt aus einem
   **Voice-Enrollment** beim Namensaufruf oder aus der Rednerliste — gekapselt in
   `speaker_map`. Stimmprofile sind biometrische Daten (Art. 9 DSGVO): Embeddings
   nur mit Rechtsgrundlage speichern, sonst pro Sitzung verwerfen.
2. **Provenienz bis zur Sekunde.** Jeder extrahierte Beschluss/jede Abstimmung
   verweist per `BELEGT_DURCH` auf das Transkriptsegment mit `start_sec`/`end_sec`.
   Im Streit­fall ist die Aussage **per Klick im Audio nachhörbar** — das macht aus
   einer KI-Zusammenfassung ein justiziables Protokoll.
3. **On-prem statt Cloud.** Whisper + pyannote + lokales LLM laufen vollständig
   im Behördennetz. Keine Sitzungsstimmen verlassen das Haus.

---

## Warum GraphRAG statt Vektor-RAG?

Protokollfragen sind **mehrhop und strukturiert** — genau dort versagt ein
Embedding-Index über Textchunks:

| Frage | Graph-Traversierung |
| ----- | ------------------- |
| „Welche Beschlüsse mit welchem Ergebnis?" | `Beschluss ←FUEHRT_ZU← Abstimmung` (Ja/Nein/Enthaltung) |
| „Wie war die Abstimmung zum Bücherbus?" | `TOP →ENTSCHIEDEN_DURCH→ Abstimmung →…→ Beschluss` |
| „Wer war befangen — nach welcher Norm?" | `Person →BEFANGEN_BEI→ TOP`, `Person →BEFANGENHEIT_NACH→ Norm §18` |
| „Welche Aufgabe, wer zuständig, welche Frist?" | `Beschluss →ERZEUGT_AUFGABE→ Aufgabe` |
| „Beleg im Audio?" | `* →BELEGT_DURCH→ Transkriptsegment.start_sec` |

Beispielausgabe (gekürzt):

```
❓ Welche Beschlüsse wurden gefasst?
📋 • Beschluss 2026-014: Online-Terminsystem … — Abstimmung 7:0:1 (angenommen)
     ↳ Audiobeleg [01:44] Dr. Petra Hoffmann: „Damit ist Beschluss 2026-014 gefasst…"
   • Beschluss 2026-015: Anschaffung Bücherbus … — Abstimmung 5:2:0 (angenommen)
     ↳ Audiobeleg [03:56] Dr. Petra Hoffmann: „Beschluss 2026-015: Die Anschaffung…"
```

---

## Vier-Schichten-Ontologie (wie in den Schwester-Prototypen)

| Schicht | Knotentypen | Beispiel |
| ------- | ----------- | -------- |
| **L1 Normativ** | `Norm` | GemO §37 (Beschlussfähigkeit), §18 (Befangenheit) |
| **L2 Zeitlich** | `Sitzung`, Fristen an `Aufgabe` | Sitzung 12.05.2026; Frist 09.06.2026 |
| **L3 Prozedural** | `Tagesordnungspunkt → Antrag → Abstimmung → Beschluss → Aufgabe` | TOP 3 → Antrag → 5:2:0 → Beschluss 2026-015 |
| **L4 Fallbezug** | `Person`, `Fraktion`, `Redebeitrag` | Klaus Brandt (GRÜN-Liste), Redebeitrag zu TOP 2 |
| **L4 Fallbezug** | `Aussage` (prüfbare Behauptung), `Frage` | „über 150.000 Ladepunkte" |
| **+ Faktencheck** | `Faktencheck` (Verdikt), `Quelle` | irreführend · Ladesäulenregister |
| **+ Provenienz** | `Transkriptsegment` | Segment [03:56], `start_sec`, `audio_file` |

---

## Faktencheck (Bundestag-Szenario)

Prüfbare Aussagen aus Reden → Verdikt + Quelle + Audio-Beleg.
Konzept, Verdikt-Skala und Grenzen:
[`docs/bundestag-protokollierung-analyse.md`](docs/bundestag-protokollierung-analyse.md).

```
🔎 Faktencheck der Reden:
• [irreführend] „über 150.000 öffentliche Ladepunkte" — Stefan Möller
    belegt: ~121.000 · Quelle: Ladesäulenregister (Stand 2026-04)   ↳ [00:18]
• [falsch]      „seit 2021 nicht erhöht" — Dr. Lena Vossberg
    mehr als verdoppelt (50.000 → 121.000)                          ↳ [00:47]
• [unbelegt]    „über 40 % der Ladesäulen defekt" — keine Evidenz   ↳ [01:44]
```

Graph: `Aussage →GEPRUEFT_ALS→ Faktencheck →BELEGT_MIT→ Quelle` (+ `BELEGT_DURCH → Transkriptsegment`).

---

## GitHub Pages (interaktiver 3D-Graph + Faktencheck-Panel)

`web/index.html` ist eine **statische** Single-File-App (`3d-force-graph` via CDN),
die `web/data/<scenario>.json` lädt — Szenario-Umschalter, Detail-Panel,
Faktencheck-Liste, Audio-Deep-Links auf `Transkriptsegment`.

```bash
python3 run_demo.py --no-queries        # web/data/*.json erzeugen
python3 -m http.server -d web 8000      # lokal: http://localhost:8000
```

Deploy: Der Workflow `.github/workflows/pages.yml` baut die Daten und publiziert
`web/` automatisch. **Eigenständiges Repo + Pages mit einem Befehl:**

```bash
./scripts/publish-to-github.sh hackathon-spark   # braucht `gh auth login`
# → https://ma3u.github.io/hackathon-spark/
```

## Amtliches Plenarprotokoll → Neo4j → GraphRAG → Dashboard

Echte Bundestagsdaten brauchen kein Audio: das **amtliche Plenarprotokoll-XML**
(DTD `dbtplenarprotokoll`, ab WP19) wird direkt geparst — inklusive der
`<kommentar>`-**Saalreaktionen** (Beifall/Zwischenruf/Lachen/Widerspruch =
Jubel/Buhrufe, amtlich annotiert). **Mitgeliefert ist eine echte Sitzung**
(`data/real/plenarprotokoll-20-214.xml`, gemeinfrei) — Szenario „Bundestag (echt)".

```bash
# Echtes mitgeliefertes Protokoll (ohne Faktencheck über reale Personen):
python ingest_bundestag.py --xml data/real/plenarprotokoll-20-214.xml \
    --name bundestag_real --no-factcheck

# Eigene Sitzung ziehen + verarbeiten:
# 1) Offizielle Quellen einer Sitzung ziehen (auf deiner Maschine):
./scripts/fetch-session.sh 21 81            # Open-Data-XML + DIP-API + YouTube-Audio
# 2) Parsen → Graph + Faktencheck + Dashboard, dry-run Neo4j:
python ingest_bundestag.py --xml data/incoming/21-081/21081.xml
# 3) Neo4j starten und echt laden:
docker compose -f docker-compose.neo4j.yml up -d
python ingest_bundestag.py --xml data/incoming/21-081/21081.xml --load
```

**Neo4j-Import** (`pipeline/neo4j_loader.py`): idempotente, **parametrisierte**
`MERGE` über den offiziellen `neo4j`-Driver (kein String-Interpolieren).

**Neo4j-GraphRAG** (`pipeline/neo4j_graphrag.py`): die **offizielle
`neo4j-graphrag`-Bibliothek** mit **Text2Cypher** — natürliche Frage →
schema-gestützter Cypher → Neo4j → Antwort (LLM on-prem via Ollama/vLLM).
Faktencheck-Fragen liefern per Few-Shot **immer Verdikt + Quelle**.

```bash
python -m pipeline.neo4j_graphrag "Welche Aussagen sind falsch — mit Quelle?"
```

**Dashboard pro Sitzung** (`pipeline/dashboard.py` → `web/data/*_dashboard.json`,
im Pages-UI über „📊 Dashboard"): Top-Themen nach Redevolumen, **Sprachanteil
pro Fraktion**, **positives/negatives Feedback** je Thema und je Fraktion (aus
den Saalreaktionen), Faktencheck-Bilanz.

**Barrierefreiheit (blinde/sehbehinderte Menschen)** (`pipeline/accessible.py`,
Pages „♿ Vorlesefassung"): lineare, screen-reader-/TTS-taugliche Textfassung der
Sitzung — inkl. **verbalisierter Saalreaktionen** (Beifall = Zustimmung,
Widerspruch/Buhrufe = Ablehnung) und Faktencheck mit Quellen.

**Gap-Analyse Protokoll ↔ Video** (`compare_protocol_video.py`,
`pipeline/gap_analysis.py`): WER, Saalreaktions-Recall, Sprecher-/Inhalts-Lücken
gegen den amtlichen Goldstandard. Methodik: `docs/test-protokoll-vs-video.md`.

**Doku:** Quellen `docs/quellen.md` · Plan/Fortschritt `docs/challenge-plan.md` ·
Fragen an den Bundestag `docs/fragen-bundestag.md`.

## Projektstruktur

```
graph-protokoll/
├── run_demo.py                 # Audio-Demo (Gemeinderat + Bundestag)
├── ingest_bundestag.py         # amtliches Plenarprotokoll-XML → Graph → Neo4j
├── pipeline/
│   ├── asr.py / diarize.py / align.py   # Audio → sprecher-attribuierte Utterances
│   ├── bundestag_xml.py        # Parser für amtliches dbtplenarprotokoll-XML (+ Saalreaktionen)
│   ├── extract.py              # Regel-/LLM-Extraktion (TOPs, Beschlüsse, Aussagen, Fragen)
│   ├── factcheck.py            # Aussagen → Verdikt + Quelle (immer)
│   ├── graph_build.py          # Protokoll → 5-Schichten-Graph (SPARK-Format)
│   ├── export.py               # JSON / CSV / Neo4j-Cypher
│   ├── neo4j_loader.py         # idempotenter, parametrisierter Import nach Neo4j
│   ├── neo4j_graphrag.py       # Neo4j-GraphRAG (Text2Cypher) — NL-Fragen über den Graphen
│   ├── dashboard.py            # Sitzungs-Kennzahlen (Themen, Sprachanteil, Feedback)
│   └── graphrag.py             # Offline-Demo-Router (ohne Neo4j/LLM)
├── docker-compose.neo4j.yml    # lokales Neo4j 5 für Import + GraphRAG
├── scripts/fetch-session.sh    # offizielle Sitzungsquellen ziehen (Open Data/DIP/YouTube)
├── data/sample/                # fiktive, diarisierte Mitschnitte
├── data/evidence/              # fiktive Evidenzbasis für den Faktencheck
├── web/                        # statische GitHub-Pages-App (+ web/data/*.json)
├── docs/                       # Bundestag-Protokollierung & Faktencheck-Analyse
├── scripts/publish-to-github.sh
├── .github/workflows/pages.yml
├── output/                     # generierte Graph-Artefakte
├── requirements.txt            # nur Produktivpfad (Demo braucht keine Deps)
├── publiccode.yml              # Public-Money-Public-Code-Metadaten (EUPL-1.2)
└── LICENSE                     # EUPL-1.2 (Volltext via publish-Skript)
```

## Demo-Daten

- **`data/sample/` — frei erfunden:** Gemeinde Musterbach, fiktive Abgeordnete/Fraktionen,
  fiktive Statistiken/Quellen. Keine realen Personen, Organisationen, Sitzungen oder Zitate.
  Der **Faktencheck** läuft nur hier (gegen den fiktiven `data/evidence/evidenz.json`) und
  demonstriert den **Mechanismus**, nicht reale Politik.
- **`data/real/` — echt:** amtliches Plenarprotokoll WP20/214 (gemeinfrei, § 5 UrhG). Daraus
  entsteht das Szenario „Bundestag (echt)" mit Graph, Saalreaktionen, Dashboard und
  Vorlesefassung — **ohne** Faktencheck-Verdikte über reale Personen (`--no-factcheck`).
  Einordnung & weitere Echtdaten-Wege (YouTube-Untertitel, eigene Sitzungen):
  [`docs/spark-und-echtdaten.md`](docs/spark-und-echtdaten.md).

## Lizenz

**EUPL-1.2** — wie die BMDS-Referenzlösung **SPARK Workflow**, im Sinne von
„Public Money – Public Code". Die `LICENSE` enthält die offizielle EUPL-Notice;
den autoritativen Volltext zieht `scripts/publish-to-github.sh` beim
Veröffentlichen (oder manuell von
<https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12>).
