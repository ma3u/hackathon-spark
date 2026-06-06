# SPARK-Nutzung & echte Daten — Einordnung

Beantwortet drei Fragen, belegt mit tatsächlich durchgeführten Schritten (Stand 2026-06-06):

1. **Wo nutzen wir SPARK** — und haben wir es lokal ausgecheckt und untersucht?
2. **Wo erweitern wir SPARK?**
3. **Werden Protokolle noch von Menschen erstellt — und kann man die YouTube-Transkripte
   nicht direkt nehmen und weiterbearbeiten?**

> Methodik-Hinweis: Anders als in `docs/quellen.md` vermerkt ist diese Arbeitsumgebung
> **nicht** netzgesperrt. Die unten gezeigten Schritte (SPARK klonen, `@bundestag`-Untertitel
> via `yt-dlp` ziehen, amtliche Protokoll-XML von Open Data laden) wurden hier **real
> ausgeführt**, nicht nur beschrieben.

---

## A. Wo nutzen wir SPARK? (ehrliche Bestandsaufnahme)

### Haben wir SPARK lokal ausgecheckt und untersucht?

**Im Repo selbst: nein.** Es gibt **keine** Code-Abhängigkeit zu SPARK — keine `.gitmodules`,
kein vendored Code, kein Eintrag in `requirements.txt`, kein Import. Bis zu dieser Analyse war
SPARK nur **per URL referenziert** (`docs/quellen.md` §6), nicht eingesehen.

**Jetzt nachgeholt:** Das offizielle Repo wurde geklont und untersucht:

```bash
git clone --depth 1 \
  https://gitlab.opencode.de/bmds/planungs-und-genehmigungsbeschleunigung/spark-workflow.git
```

### Was SPARK Workflow tatsächlich ist (Befund)

Eine **Microservice-Plattform zur Dokumentenverarbeitung** für **Planungs- und
Genehmigungsverfahren** (BMDS, EUPL-1.2, „Public Money – Public Code"; in drei Releases
veröffentlicht). Stack laut `docker-compose.*.yaml`:

| Bereich | SPARK Workflow nutzt |
| ------- | -------------------- |
| Sprache/Framework | Python 3.13, FastAPI |
| Orchestrierung | **Temporal** (1.29) — durabler Workflow-Server |
| Speicher | **Postgres** 16, **MinIO/S3**, **Elasticsearch** 7.17 |
| Retrieval | **Qdrant** (Vektor-DB → **Vektor-RAG**) |
| Dokument-Parsing | **Docling** |
| LLM (on-prem) | **LiteLLM / vLLM** (OpenAI-kompatibler Endpoint) |
| Module (Release 1) | Inhaltsextraktion · formale Vollständigkeitsprüfung · Plausibilitätsprüfung · agent_orchestration / document_management / project_logic / comment + temporal-Dienste |

**Wichtig:** SPARK Workflow enthält **keinen Knowledge Graph, kein Neo4j, keine Ontologie,
kein GraphRAG** — geprüft per Volltextsuche, **null Treffer**. SPARK macht **Vektor-RAG über
Qdrant**, nicht Graph-RAG.

### Klarstellung zu den „Schwester-Prototypen"

README/`publiccode.yml` sprechen vom „gemeinsamen SPARK-Datenformat der Schwester-Prototypen
**graph-insurance / graph-investigation / graph-eAkte**". Diese Repos **existieren** — aber
unter **`github.com/ma3u`** (dein eigener Account), **nicht** unter BMDS:

```
graph-insurance @ma3u → EXISTIERT   graph-investigation @ma3u → EXISTIERT   graph-eAkte @ma3u → EXISTIERT
graph-* @bmds → existiert nicht
```

Das „SPARK-Datenformat" (`{metadata, nodes, relationships}` + 4/5-Schichten-Ontologie) stammt
also aus **deinem eigenen Prototypen-Ökosystem**, nicht aus dem offiziellen SPARK Workflow.

### Was wir konkret mit SPARK teilen (konzeptionell, nicht als Code)

- **Mission:** SPARK-Hackathon **Challenge 2 „Da geht noch mehr!"** — die KI-Bausteine auf
  eine **neue Verwaltungsleistung jenseits von Planung/Genehmigung** übertragen.
- **Lizenz/Haltung:** EUPL-1.2, Public Money – Public Code (wie BMDS SPARK).
- **On-prem-LLM-Muster:** OpenAI-kompatibler lokaler Endpoint. SPARK: LiteLLM/vLLM; wir:
  Ollama/vLLM in `pipeline/neo4j_graphrag.py` (`base_url`) und `extract.EXTRACTION_PROMPT`.
- **Analoge Bausteine:** SPARKs *Inhaltsextraktion* ≈ unser `pipeline/extract.py`; SPARKs
  *Vollständigkeits-/Plausibilitätsprüfung* ≈ konzeptionell unser Qualitäts-/Faktencheck.

---

## B. Wo erweitern wir SPARK?

`graph-protokoll` fügt eine **neue Verwaltungs-/Parlamentsleistung** hinzu (Gremien-/
Plenarprotokoll-Analyse) und bringt Bausteine, die SPARK Workflow nicht hat:

| Fähigkeit | SPARK Workflow | graph-protokoll (Erweiterung) |
| --------- | -------------- | ----------------------------- |
| Eingabe | Dokumente (PDF/DOCX via Docling) | **Audio/Video (ASR)** + amtliches **Plenarprotokoll-XML** + **YouTube-Untertitel** |
| Sprecher | — | **Diarisierung** (pyannote) + Sprecher↔Person-Auflösung |
| Saalreaktionen | — | **Sound-Event-Detection** (PANNs) + `<kommentar>` aus XML (Beifall/Zwischenruf/…) |
| Retrieval | Vektor-RAG (Qdrant) | **Knowledge Graph (Neo4j) + GraphRAG/Text2Cypher** |
| Provenienz | Dokumentbezug | **Audio-Sekunde** (`BELEGT_DURCH → Transkriptsegment`) |
| Bewertung | formale/Plausibilitätsprüfung | **Faktencheck mit Quellen-Provenienz** (Verdikt + Quelle) |
| Ausgabe | Verfahrensschritte | **Dashboard** je Sitzung + **barrierefreie Vorlesefassung** |
| Betrieb | Docker/Temporal-Cluster | **stdlib-Demo ohne Abhängigkeiten** + optionaler Produktivpfad |

Kurz: zwei generisch nützliche neue Bausteine für den SPARK-Baukasten — **ASR als Eingabe**
(statt nur Dokumente/TTS) und **Graph + Faktencheck mit Provenienz** (statt Vektor-RAG).

---

## C. Echte Daten statt fiktiver — was geht (real geprüft)

Die mitgelieferten Beispiele (`data/sample/*.diarized.json`, `*.vtt`,
`plenarprotokoll-21-081-sample.xml`, `data/evidence/evidenz.json`) sind **frei erfunden**.
Beide Echtdaten-Wege funktionieren — hier real ausgeführt:

### Weg 1 — Amtliches Plenarprotokoll-XML (Goldstandard) ✅ empfohlen

```bash
# Echte XML-Links liefert die Open-Data-Liste (Blob-IDs nicht ableitbar → über die Liste):
curl -sSL "https://www.bundestag.de/ajax/filterlist/de/dokumente/protokolle/plenarprotokolle/866354-866354?limit=5&noFilterSet=true" \
  | grep -oiE 'href="[^"]*\.xml"'
# → z. B. https://www.bundestag.de/resource/blob/1057624/20214.xml  (WP20, Sitzung 214)
curl -sSL -o real.xml "https://www.bundestag.de/resource/blob/1057624/20214.xml"
python3 ingest_bundestag.py --xml real.xml          # → Graph + Faktencheck + Dashboard (dry-run Neo4j)
```

**Ergebnis (echte Sitzung WP20/214, 18.03.2025):** 45 Reden, 139 prüfbare Aussagen,
**638 amtliche Saalreaktionen** (388× Beifall, 81× Zwischenruf, 9× Lachen …), Graph mit
**1075 Knoten / 2780 Beziehungen**; echte Redner:innen (Johannes Vogel, Dr. Johannes Fechner,
Dr. Bernd Baumann …). Amtliche Protokolle sind **gemeinfrei** (§ 5 UrhG) — rechtlich
unbedenklich. *Gefundene Schwäche:* die TOP-Erkennung griff nur 1 TOP (der Parser iteriert
`tagesordnungspunkt`, übersieht `zusatzpunkt`/`sitzungsbeginn`) → `bundestag_xml.py` für
Echtdaten nachschärfen.

### Weg 2 — YouTube-Untertitel von `@bundestag` ✅ funktioniert, mit Vorbehalt

```bash
yt-dlp --write-auto-subs --sub-langs "de" --convert-subs vtt --skip-download \
  -o "vid.%(ext)s" "https://www.youtube.com/watch?v=<VIDEO_ID>"
python3 -c "from pipeline import subtitles, json; \
  print(json.dumps(subtitles.to_diarized('vid.de.vtt')))" > diarized.json
```

**Befund (echtes Video, 80. Sitzung 21.05.2026, TOP 20):** Untertitel sind **automatische
Captions = YouTubes eigenes ASR** (keine menschlich erstellten Untertitel). Die Pipeline
verarbeitet sie, aber die Qualität zeigt klar die Grenzen (siehe Teil D).

---

## D. Werden Protokolle noch von Menschen erstellt? Reichen YouTube-Transkripte?

### Werden sie noch von Menschen erstellt? — Ja, überwiegend.

Pro Sitzungstag schreiben **~16 Parlamentsstenograf:innen** wörtlich mit (Ablösung alle
5 Min., bis ~500 Silben/Min.), erfassen **auch jeden Zwischenruf und Beifall**, übertragen die
Kurzschrift in Volltext und recherchieren Unklares. Spracherkennung wird **„inzwischen
teilweise"** unterstützend genutzt — der Prozess ist also **noch nicht** voll automatisiert.
Redner:innen haben ein **Korrekturrecht** (Sinn darf sich nicht ändern). Ein **vorläufiges**
Protokoll erscheint am Sitzungstag, das **endgültige** am Folgewerktag als PDF/**XML**.
(Quelle: `docs/bundestag-protokollierung-analyse.md` §6, Bundestag-Stenografen-Seite.)

### Kann man die YouTube-Transkripte nicht direkt nehmen?

**Technisch ja — als schneller Rohentwurf — aber nicht als Endprodukt.** Real getestet an
einem `@bundestag`-Video (14 Min., TOP 20). Die rohen Auto-Captions haben drei harte Mängel:

| Problem (real beobachtet) | Wirkung | Was die Pipeline leisten muss |
| ------------------------- | ------- | ----------------------------- |
| **Keine Sprecher-Labels** | 14-Min-Debatte landete als **3 Blöcke „UNBEKANNT"** statt vieler Redebeiträge | Diarisierung / Rednerliste-Enrollment |
| **Rollende Doppelzeilen** | Text dreifach dupliziert („…eine Beratung in Tagesordnungspunkt 20 eine Beratung…") → Extraktion verrauscht | Dedup im VTT-Parser nötig |
| **Keine Satzzeichen/Saalreaktionen** | kein Beifall/Zwischenruf, schlechte Satztrennung | Punktuierung + Sound-Event-Detection |

**Empfehlung — Hybrid (genau die Lücke, die `graph-protokoll` füllt):**
1. **Goldstandard = amtliches XML** (gemeinfrei, mit Saalreaktionen, korrigiert) für die
   belastbare Auswertung — Weg 1.
2. **Near-Realtime-Entwurf** = YouTube-Captions **oder** eigenes Whisper-ASR auf dem
   Mediathek-/YouTube-Audio (genauer als Auto-Captions, mit Wort-Zeitstempeln) — für den
   schnellen Zwischenlayer am Sitzungstag, bevor das XML vorliegt.
3. **Veredelung durch die Pipeline:** Dedup + Diarisierung + Saalreaktionen (SED) + Extraktion
   → Graph + Provenienz. Der Mehrwert ist nicht „Transkript haben", sondern **Struktur +
   Sprecher + Belege**.
4. **Qualität messbar:** `compare_protocol_video.py` (WER, Saalreaktions-Recall) quantifiziert
   den Abstand Entwurf ↔ Gold — und respektiert das **Korrekturrecht** (Differenz = Diff,
   nicht „falsch").

### ⚠️ Faktencheck mit echten Personen — Vorsicht (real belegt)

Der Demo-Faktencheck (`factcheck_rule_based`) gleicht per Schlüsselwort gegen den **fiktiven**
`evidenz.json` ab. Auf das **echte** Protokoll WP20/214 angewandt erzeugte er **1× „falsch"**
auf die Aussage einer **realen, namentlich genannten Abgeordneten** — ein **Fehlurteil**
(Keyword-Zufallstreffer gegen erfundene Evidenz). Daraus folgt:

- Automatisierte „falsch/irreführend"-Verdikte über **reale Personen** öffentlich (GitHub
  Pages) zu publizieren ist **rechtlich/ethisch heikel** (Persönlichkeitsrecht) und mit dem
  Demo-Checker **sachlich unzuverlässig**.
- Produktiv nötig: ein **echter Evidenzkorpus** (Destatis/Bundesregierung/Drucksachen via
  DIP-API) + LLM-NLI-Verifizierer **mit Zitatpflicht** + **Mensch-im-Loop/Widerspruchspfad**.
- Empfehlung: Echtdaten gern für **Transkript, Graph, Saalreaktionen, Dashboard,
  Barrierefreiheit** — den **Faktencheck auf reale Namen** aber nicht ungeprüft veröffentlichen,
  bis Korpus + Verifizierer + Freigabeprozess stehen (Grundsatz „Quelle immer", `unbelegt ≠
  falsch` bleibt erhalten).
